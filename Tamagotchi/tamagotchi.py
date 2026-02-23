"""
Terminal Tamagotchi — single-file implementation.
Python 3.10+  |  stdlib only
"""

import os
import sys
import json
import time
import copy

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAVE_PATH = "/workspace/claude_agents/tamagotchi_save.json"
BAR_WIDTH = 10

DECAY = {
    "hunger": 5,
    "energy": 4,
    "happiness": 2,
}

FACES = {
    "happy":    "(^‿^)",
    "neutral":  "(-_-)",
    "sad":      "(;_;)",
    "sleeping": "(-.-)zzZ",
    "dead":     "(x_x)",
}

INITIAL_STATS = {
    "hunger":    80,
    "happiness": 80,
    "energy":    80,
    "health":    100,
}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def clamp(value, lo, hi):
    """Return value clamped to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Pet factory
# ---------------------------------------------------------------------------


def make_pet(name: str) -> dict:
    """Return an initial pet dict with all stats at starting values."""
    return {
        "name":                 name,
        "hunger":               80,
        "happiness":            80,
        "energy":               80,
        "health":               100,
        "turn":                 1,
        "alive":                True,
        "sleeping":             False,
        "sleep_turns_remaining": 0,
    }


# ---------------------------------------------------------------------------
# Stat logic
# ---------------------------------------------------------------------------


def decay_stats(pet):
    """Apply per-turn decay to hunger, energy, and happiness. Clamp to [0, 100]."""
    for stat, amount in DECAY.items():
        pet[stat] = clamp(pet[stat] - amount, 0, 100)


def check_health_drain(pet):
    """If hunger == 0, subtract 10 from health and clamp to [0, 100]."""
    if pet["hunger"] == 0:
        pet["health"] = clamp(pet["health"] - 10, 0, 100)


def check_death(pet):
    """If health <= 0, mark pet as dead."""
    if pet["health"] <= 0:
        pet["alive"] = False


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def apply_feed(pet):
    """Add 30 to hunger, capped at 100."""
    pet["hunger"] = clamp(pet["hunger"] + 30, 0, 100)


def apply_play(pet):
    """Add 20 to happiness, subtract 15 from energy; both clamped to [0, 100]."""
    pet["happiness"] = clamp(pet["happiness"] + 20, 0, 100)
    pet["energy"]    = clamp(pet["energy"] - 15, 0, 100)


def start_sleep(pet):
    """Begin a sleep cycle: 3 automatic turns of rest."""
    pet["sleeping"]              = True
    pet["sleep_turns_remaining"] = 3


def process_sleep_turn(pet):
    """Advance one sleep turn: restore 25 energy; wake up when counter hits 0."""
    pet["energy"]               = clamp(pet["energy"] + 25, 0, 100)
    pet["sleep_turns_remaining"] -= 1
    if pet["sleep_turns_remaining"] <= 0:
        pet["sleeping"]              = False
        pet["sleep_turns_remaining"] = 0


# ---------------------------------------------------------------------------
# Mood
# ---------------------------------------------------------------------------


def get_mood(pet) -> str:
    """Derive mood string from current stats."""
    if pet["sleeping"]:
        return "sleeping"
    h  = pet["hunger"]
    hp = pet["happiness"]
    e  = pet["energy"]
    if h >= 50 and hp >= 50 and e >= 30:
        return "happy"
    if h < 25 or hp < 25 or e < 20:
        return "sad"
    return "neutral"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_bar(label: str, value: int, width: int = 10) -> str:
    """Return a formatted stat bar string, e.g. 'Hunger    [########..] 80/100'."""
    filled = round(value / 100 * width)
    bar    = "#" * filled + "." * (width - filled)
    padded_label = label.ljust(10)
    return f"{padded_label}[{bar}] {value}/100"


def render_pet(pet):
    """Print the full turn display to stdout."""
    mood = get_mood(pet)
    face = FACES.get(mood, FACES["neutral"])

    print(f"=== Tamagotchi — Turn {pet['turn']} ===")
    print()
    print(face)
    print()
    print(render_bar("Hunger",    pet["hunger"]))
    print(render_bar("Happiness", pet["happiness"]))
    print(render_bar("Energy",    pet["energy"]))
    print(render_bar("Health",    pet["health"]))
    print()
    print(f"Mood: {mood.capitalize()}")


def render_death(pet):
    """Print the death screen box."""
    name      = pet["name"]
    turn      = pet["turn"]
    face_line = FACES["dead"]

    inner_width = 23
    box_top    = "+" + "-" * inner_width + "+"
    box_bottom = "+" + "-" * inner_width + "+"

    def box_line(text: str) -> str:
        return "|" + text.center(inner_width) + "|"

    print(box_top)
    print(box_line(face_line))
    print(box_line(f"{name} has passed away."))
    print(box_line(f"Survived: {turn} turns"))
    print(box_bottom)


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


def clear_screen():
    """Clear the terminal using the OS-appropriate command."""
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------


def save_game(pet):
    """Serialise pet dict to JSON and write to SAVE_PATH."""
    with open(SAVE_PATH, "w", encoding="utf-8") as fh:
        json.dump(pet, fh, indent=2)
    print("Game saved.")


def load_game():
    """Load and return pet dict from SAVE_PATH, or None if missing/corrupt."""
    if not os.path.exists(SAVE_PATH):
        return None
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def delete_save():
    """Remove SAVE_PATH if it exists; silently do nothing otherwise."""
    try:
        os.remove(SAVE_PATH)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


def prompt_action() -> str:
    """Print the action menu and return a validated single-character choice."""
    valid = {"f", "p", "s", "c", "S", "q"}
    while True:
        print("\n[f]eed  [p]lay  [s]leep  [c]heck  [S]ave  [q]uit")
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return "q"
        if not raw:
            continue
        ch = raw[0]
        if ch == "S":
            return "save"
        if ch in valid:
            return ch


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------


def run_game():
    """Entry point: handle save/load, then run the main game loop."""
    # --- startup ---
    pet = None
    if os.path.exists(SAVE_PATH):
        try:
            answer = input("Save file found. Load it? [y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if answer == "y":
            pet = load_game()

    if pet is None:
        try:
            name = input("Enter your pet's name: ").strip() or "Pip"
        except (EOFError, KeyboardInterrupt):
            name = "Pip"
        pet = make_pet(name)

    # --- main loop ---
    while pet["alive"]:
        clear_screen()
        render_pet(pet)

        if pet["sleeping"]:
            process_sleep_turn(pet)
            time.sleep(0.8)
            decay_stats(pet)
            check_health_drain(pet)
            check_death(pet)
            if pet["alive"]:
                pet["turn"] += 1
            continue

        action = prompt_action()

        if action == "f":
            apply_feed(pet)
        elif action == "p":
            apply_play(pet)
        elif action == "s":
            start_sleep(pet)
        elif action == "c":
            pass  # no stat change
        elif action == "save":
            save_game(pet)
            time.sleep(1)
            continue  # do NOT decay this turn
        elif action == "q":
            save_game(pet)
            sys.exit(0)

        decay_stats(pet)
        check_health_drain(pet)
        check_death(pet)
        if pet["alive"]:
            pet["turn"] += 1

    # --- death screen ---
    clear_screen()
    render_death(pet)
    delete_save()
    input("Press Enter to exit.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_game()
