"""
Unit tests for tamagotchi.py
Run with: python3 /workspace/claude_agents/test_tamagotchi.py
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure the module under test is importable regardless of cwd.
sys.path.insert(0, "/workspace/claude_agents")

import tamagotchi as T


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def fresh_pet(name="Test"):
    return T.make_pet(name)


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

class TestClamp(unittest.TestCase):
    def test_below_lo(self):
        self.assertEqual(T.clamp(-5, 0, 100), 0)

    def test_above_hi(self):
        self.assertEqual(T.clamp(150, 0, 100), 100)

    def test_within_range(self):
        self.assertEqual(T.clamp(50, 0, 100), 50)

    def test_exactly_lo(self):
        self.assertEqual(T.clamp(0, 0, 100), 0)

    def test_exactly_hi(self):
        self.assertEqual(T.clamp(100, 0, 100), 100)


# ---------------------------------------------------------------------------
# make_pet
# ---------------------------------------------------------------------------

class TestMakePet(unittest.TestCase):
    def setUp(self):
        self.pet = T.make_pet("Pip")

    def test_name(self):
        self.assertEqual(self.pet["name"], "Pip")

    def test_hunger(self):
        self.assertEqual(self.pet["hunger"], 80)

    def test_happiness(self):
        self.assertEqual(self.pet["happiness"], 80)

    def test_energy(self):
        self.assertEqual(self.pet["energy"], 80)

    def test_health(self):
        self.assertEqual(self.pet["health"], 100)

    def test_turn(self):
        self.assertEqual(self.pet["turn"], 1)

    def test_alive(self):
        self.assertTrue(self.pet["alive"])

    def test_sleeping(self):
        self.assertFalse(self.pet["sleeping"])

    def test_sleep_turns_remaining(self):
        self.assertEqual(self.pet["sleep_turns_remaining"], 0)

    def test_all_keys_present(self):
        expected_keys = {
            "name", "hunger", "happiness", "energy", "health",
            "turn", "alive", "sleeping", "sleep_turns_remaining",
        }
        self.assertEqual(set(self.pet.keys()), expected_keys)


# ---------------------------------------------------------------------------
# decay_stats
# ---------------------------------------------------------------------------

class TestDecayStats(unittest.TestCase):
    def test_hunger_decays(self):
        pet = fresh_pet()
        T.decay_stats(pet)
        self.assertEqual(pet["hunger"], 75)  # 80 - 5

    def test_energy_decays(self):
        pet = fresh_pet()
        T.decay_stats(pet)
        self.assertEqual(pet["energy"], 76)  # 80 - 4

    def test_happiness_decays(self):
        pet = fresh_pet()
        T.decay_stats(pet)
        self.assertEqual(pet["happiness"], 78)  # 80 - 2

    def test_health_not_affected(self):
        pet = fresh_pet()
        T.decay_stats(pet)
        self.assertEqual(pet["health"], 100)  # unchanged

    def test_hunger_clamped_at_zero(self):
        pet = fresh_pet()
        pet["hunger"] = 3
        T.decay_stats(pet)
        self.assertEqual(pet["hunger"], 0)  # 3 - 5 = -2 -> clamped to 0

    def test_energy_clamped_at_zero(self):
        pet = fresh_pet()
        pet["energy"] = 2
        T.decay_stats(pet)
        self.assertEqual(pet["energy"], 0)

    def test_happiness_clamped_at_zero(self):
        pet = fresh_pet()
        pet["happiness"] = 1
        T.decay_stats(pet)
        self.assertEqual(pet["happiness"], 0)


# ---------------------------------------------------------------------------
# check_health_drain
# ---------------------------------------------------------------------------

class TestCheckHealthDrain(unittest.TestCase):
    def test_health_drops_when_hunger_zero(self):
        pet = fresh_pet()
        pet["hunger"] = 0
        T.check_health_drain(pet)
        self.assertEqual(pet["health"], 90)

    def test_health_unchanged_when_hunger_positive(self):
        pet = fresh_pet()
        pet["hunger"] = 1
        T.check_health_drain(pet)
        self.assertEqual(pet["health"], 100)

    def test_health_clamped_at_zero(self):
        pet = fresh_pet()
        pet["hunger"] = 0
        pet["health"] = 5
        T.check_health_drain(pet)
        self.assertEqual(pet["health"], 0)

    def test_feeding_stops_health_drain(self):
        """After feeding the pet so hunger > 0, health stops draining."""
        pet = fresh_pet()
        pet["hunger"] = 0
        T.check_health_drain(pet)
        self.assertEqual(pet["health"], 90)
        # Now feed the pet
        T.apply_feed(pet)       # hunger = 30
        T.check_health_drain(pet)
        self.assertEqual(pet["health"], 90)  # should NOT have dropped again


# ---------------------------------------------------------------------------
# check_death
# ---------------------------------------------------------------------------

class TestCheckDeath(unittest.TestCase):
    def test_alive_set_false_when_health_zero(self):
        pet = fresh_pet()
        pet["health"] = 0
        T.check_death(pet)
        self.assertFalse(pet["alive"])

    def test_alive_set_false_when_health_below_zero(self):
        pet = fresh_pet()
        pet["health"] = -1
        T.check_death(pet)
        self.assertFalse(pet["alive"])

    def test_alive_remains_true_when_health_positive(self):
        pet = fresh_pet()
        pet["health"] = 1
        T.check_death(pet)
        self.assertTrue(pet["alive"])


# ---------------------------------------------------------------------------
# apply_feed
# ---------------------------------------------------------------------------

class TestApplyFeed(unittest.TestCase):
    def test_hunger_increases_by_30(self):
        pet = fresh_pet()
        pet["hunger"] = 50
        T.apply_feed(pet)
        self.assertEqual(pet["hunger"], 80)

    def test_hunger_capped_at_100(self):
        pet = fresh_pet()
        pet["hunger"] = 80
        T.apply_feed(pet)
        self.assertEqual(pet["hunger"], 100)

    def test_hunger_at_100_stays_100(self):
        pet = fresh_pet()
        pet["hunger"] = 100
        T.apply_feed(pet)
        self.assertEqual(pet["hunger"], 100)


# ---------------------------------------------------------------------------
# apply_play
# ---------------------------------------------------------------------------

class TestApplyPlay(unittest.TestCase):
    def test_happiness_increases_by_20(self):
        pet = fresh_pet()
        pet["happiness"] = 50
        T.apply_play(pet)
        self.assertEqual(pet["happiness"], 70)

    def test_energy_decreases_by_15(self):
        pet = fresh_pet()
        pet["energy"] = 50
        T.apply_play(pet)
        self.assertEqual(pet["energy"], 35)

    def test_happiness_capped_at_100(self):
        pet = fresh_pet()
        pet["happiness"] = 90
        T.apply_play(pet)
        self.assertEqual(pet["happiness"], 100)

    def test_energy_clamped_at_zero(self):
        pet = fresh_pet()
        pet["energy"] = 0
        T.apply_play(pet)
        self.assertEqual(pet["energy"], 0)  # 0 - 15 = -15 -> clamped to 0

    def test_energy_near_zero_clamped(self):
        pet = fresh_pet()
        pet["energy"] = 5
        T.apply_play(pet)
        self.assertEqual(pet["energy"], 0)  # 5 - 15 = -10 -> clamped to 0


# ---------------------------------------------------------------------------
# start_sleep
# ---------------------------------------------------------------------------

class TestStartSleep(unittest.TestCase):
    def test_sleeping_flag_set(self):
        pet = fresh_pet()
        T.start_sleep(pet)
        self.assertTrue(pet["sleeping"])

    def test_sleep_turns_remaining_set_to_3(self):
        pet = fresh_pet()
        T.start_sleep(pet)
        self.assertEqual(pet["sleep_turns_remaining"], 3)


# ---------------------------------------------------------------------------
# process_sleep_turn
# ---------------------------------------------------------------------------

class TestProcessSleepTurn(unittest.TestCase):
    def test_energy_increases_by_25(self):
        pet = fresh_pet()
        pet["energy"] = 40
        T.start_sleep(pet)
        T.process_sleep_turn(pet)
        self.assertEqual(pet["energy"], 65)

    def test_energy_capped_at_100(self):
        pet = fresh_pet()
        pet["energy"] = 90
        T.start_sleep(pet)
        T.process_sleep_turn(pet)
        self.assertEqual(pet["energy"], 100)

    def test_sleep_turns_remaining_counts_down(self):
        pet = fresh_pet()
        T.start_sleep(pet)
        T.process_sleep_turn(pet)
        self.assertEqual(pet["sleep_turns_remaining"], 2)

    def test_sleeping_becomes_false_after_3_calls(self):
        pet = fresh_pet()
        pet["energy"] = 0
        T.start_sleep(pet)
        T.process_sleep_turn(pet)
        T.process_sleep_turn(pet)
        T.process_sleep_turn(pet)
        self.assertFalse(pet["sleeping"])

    def test_sleep_turns_remaining_zero_after_3_calls(self):
        pet = fresh_pet()
        T.start_sleep(pet)
        T.process_sleep_turn(pet)
        T.process_sleep_turn(pet)
        T.process_sleep_turn(pet)
        self.assertEqual(pet["sleep_turns_remaining"], 0)

    def test_still_sleeping_after_2_calls(self):
        pet = fresh_pet()
        T.start_sleep(pet)
        T.process_sleep_turn(pet)
        T.process_sleep_turn(pet)
        self.assertTrue(pet["sleeping"])


# ---------------------------------------------------------------------------
# get_mood
# ---------------------------------------------------------------------------

class TestGetMood(unittest.TestCase):
    def _pet_with(self, hunger, happiness, energy, sleeping=False):
        pet = fresh_pet()
        pet["hunger"]    = hunger
        pet["happiness"] = happiness
        pet["energy"]    = energy
        pet["sleeping"]  = sleeping
        return pet

    def test_happy(self):
        pet = self._pet_with(50, 50, 30)
        self.assertEqual(T.get_mood(pet), "happy")

    def test_happy_high_values(self):
        pet = self._pet_with(80, 80, 80)
        self.assertEqual(T.get_mood(pet), "happy")

    def test_sad_low_hunger(self):
        pet = self._pet_with(24, 80, 80)
        self.assertEqual(T.get_mood(pet), "sad")

    def test_sad_low_happiness(self):
        pet = self._pet_with(80, 24, 80)
        self.assertEqual(T.get_mood(pet), "sad")

    def test_sad_low_energy(self):
        pet = self._pet_with(80, 80, 19)
        self.assertEqual(T.get_mood(pet), "sad")

    def test_neutral(self):
        # Not sad, not happy
        pet = self._pet_with(40, 40, 25)
        self.assertEqual(T.get_mood(pet), "neutral")

    def test_sleeping_overrides_stats(self):
        # Even if stats are happy, sleeping flag wins
        pet = self._pet_with(80, 80, 80, sleeping=True)
        self.assertEqual(T.get_mood(pet), "sleeping")

    def test_sleeping_overrides_sad_stats(self):
        pet = self._pet_with(0, 0, 0, sleeping=True)
        self.assertEqual(T.get_mood(pet), "sleeping")

    # Boundary tests
    def test_happy_exact_boundary(self):
        """hunger=50, happiness=50, energy=30 is exactly happy."""
        pet = self._pet_with(50, 50, 30)
        self.assertEqual(T.get_mood(pet), "happy")

    def test_sad_hunger_boundary(self):
        """hunger=24 returns sad even if other stats are high."""
        pet = self._pet_with(24, 100, 100)
        self.assertEqual(T.get_mood(pet), "sad")

    def test_not_sad_at_hunger_25(self):
        """hunger=25 alone does not trigger sad (threshold is < 25).
        With hunger=25 < happy threshold of 50, result is neutral."""
        pet = self._pet_with(25, 50, 30)
        # hunger=25 is not < 25 so not sad; but hunger=25 < 50 so not happy either
        self.assertEqual(T.get_mood(pet), "neutral")


# ---------------------------------------------------------------------------
# render_bar
# ---------------------------------------------------------------------------

class TestRenderBar(unittest.TestCase):
    def test_full_bar(self):
        result = T.render_bar("Hunger", 100)
        self.assertIn("##########", result)
        self.assertNotIn(".", result.split("]")[0])  # no dots in bar section

    def test_empty_bar(self):
        result = T.render_bar("Hunger", 0)
        self.assertIn(".........." , result)
        self.assertNotIn("#", result.split("]")[0])  # no fills in bar section

    def test_half_bar(self):
        result = T.render_bar("Hunger", 50)
        # round(50/100*10) = 5
        self.assertIn("#####.....", result)

    def test_value_string_present(self):
        result = T.render_bar("Hunger", 80)
        self.assertIn("80/100", result)

    def test_label_present(self):
        result = T.render_bar("Hunger", 80)
        self.assertIn("Hunger", result)

    def test_brackets_present(self):
        result = T.render_bar("Hunger", 80)
        self.assertIn("[", result)
        self.assertIn("]", result)

    def test_partial_bar_correct_fills(self):
        # value=30 -> round(30/100*10) = 3 filled
        result = T.render_bar("Energy", 30)
        self.assertIn("###.......", result)

    def test_label_padded_to_10(self):
        result = T.render_bar("HP", 50)
        # "HP" left-justified to 10 chars
        self.assertTrue(result.startswith("HP        "))

    def test_zero_value_string(self):
        result = T.render_bar("Health", 0)
        self.assertIn("0/100", result)


# ---------------------------------------------------------------------------
# save_game / load_game / delete_save
# ---------------------------------------------------------------------------

TEST_SAVE_PATH = "/tmp/test_tamagotchi_save.json"


class TestSaveLoad(unittest.TestCase):
    def setUp(self):
        # Redirect SAVE_PATH to a temp location
        self._orig_save_path = T.SAVE_PATH
        T.SAVE_PATH = TEST_SAVE_PATH
        # Clean up before each test
        if os.path.exists(TEST_SAVE_PATH):
            os.remove(TEST_SAVE_PATH)

    def tearDown(self):
        T.SAVE_PATH = self._orig_save_path
        if os.path.exists(TEST_SAVE_PATH):
            os.remove(TEST_SAVE_PATH)

    def test_save_writes_file(self):
        pet = fresh_pet()
        with patch("builtins.print"):  # suppress "Game saved."
            T.save_game(pet)
        self.assertTrue(os.path.exists(TEST_SAVE_PATH))

    def test_save_writes_valid_json(self):
        pet = fresh_pet()
        with patch("builtins.print"):
            T.save_game(pet)
        with open(TEST_SAVE_PATH) as fh:
            data = json.load(fh)
        self.assertIsInstance(data, dict)

    def test_load_returns_equivalent_dict(self):
        pet = fresh_pet()
        with patch("builtins.print"):
            T.save_game(pet)
        loaded = T.load_game()
        self.assertEqual(loaded, pet)

    def test_load_returns_none_when_absent(self):
        result = T.load_game()
        self.assertIsNone(result)

    def test_load_returns_none_on_corrupt_file(self):
        with open(TEST_SAVE_PATH, "w") as fh:
            fh.write("not json{{{")
        result = T.load_game()
        self.assertIsNone(result)

    def test_delete_save_removes_file(self):
        pet = fresh_pet()
        with patch("builtins.print"):
            T.save_game(pet)
        T.delete_save()
        self.assertFalse(os.path.exists(TEST_SAVE_PATH))

    def test_delete_save_no_error_when_absent(self):
        # Should not raise
        try:
            T.delete_save()
        except Exception as exc:
            self.fail(f"delete_save raised {exc}")


# ---------------------------------------------------------------------------
# No third-party imports
# ---------------------------------------------------------------------------

class TestNoThirdPartyImports(unittest.TestCase):
    STDLIB_MODULES = {
        "os", "sys", "json", "time", "copy", "unittest",
        "unittest.mock", "builtins", "abc", "io", "re",
        "collections", "itertools", "functools", "math",
        "string", "typing", "types", "warnings", "traceback",
        "contextlib", "pathlib", "shutil", "tempfile",
        "tamagotchi",  # the module itself
    }

    def test_tamagotchi_stdlib_only(self):
        import importlib
        import importlib.util
        # Read the source file and check for import statements
        src_path = "/workspace/claude_agents/tamagotchi.py"
        with open(src_path) as fh:
            source = fh.read()
        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    self.assertIn(top, self.STDLIB_MODULES,
                                  f"Non-stdlib import found: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    self.assertIn(top, self.STDLIB_MODULES,
                                  f"Non-stdlib import found: from {node.module}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
