import unittest

from narrative.longform.social_engine import SocialEngine, SocialEngineError
from narrative.longform.topology_pilot import run_four_world_pilot, run_topology_pilot


class SocialEngineTests(unittest.TestCase):
    def test_same_period_views_are_frozen(self):
        e = SocialEngine()
        states = {
            "lin_jing": {"cash": 38000, "weekly_hours": 40},
            "chen_lan": {"cash": 14000, "weekly_hours": 34},
        }
        first = e.freeze_views("w1", states)
        e.allocate_option("chen_lan", "seek_transition_housing", "2026-03-02")
        second = e.freeze_views("w1", states)
        self.assertEqual(first, second)

    def test_household_obligation_consumes_time_and_cash(self):
        e = SocialEngine()
        before = e.household_week("chen_lan", "2026-03-02", 14600, 38)
        e.set_household_obligation("chen_lan", "2026-03-03", 1800, 7)
        after = e.household_week("chen_lan", "2026-03-09", 14600, 38)
        self.assertLess(after["cash_after"], before["cash_after"])
        self.assertLess(after["hours_after"], before["hours_after"])

    def test_reputation_needs_received_message(self):
        e = SocialEngine()
        msg = e.communicate("sun_jie", "shen_yan", "fact", "2026-03-02")
        with self.assertRaises(SocialEngineError):
            e.reputation_from_message("wu_cheng", "chen_lan", "reliability", .2, msg, "2026-03-03")


class PilotTests(unittest.TestCase):
    def test_one_world_runs_160_weeks(self):
        r = run_topology_pilot(101, 160)
        self.assertEqual(r["weeks"], 160)
        self.assertEqual(r["status"], "pilot_noncanonical")

    def test_four_world_acceptance_requires_closed_chains(self):
        result = run_four_world_pilot()
        self.assertEqual(len(result["worlds"]), 4)
        self.assertTrue(result["acceptance"])
        self.assertGreaterEqual(result["total_closed_chains"], 3)
        self.assertGreaterEqual(result["worlds_with_at_least_three_chains"], 1)


if __name__ == "__main__":
    unittest.main()
