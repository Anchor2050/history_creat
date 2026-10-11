import unittest

from narrative.longform.career_six_continuity_v2 import (
    JOB_CYCLE_YEARS,
    simulate_career_six_continuity,
)


class CareerSixContinuityV2Tests(unittest.TestCase):
    def test_search_window_is_continuous_through_2031(self):
        self.assertEqual(JOB_CYCLE_YEARS, tuple(range(2026, 2032)))

    def test_shared_public_sector_capacity_creates_cross_actor_conflict(self):
        run = simulate_career_six_continuity(seed=1)
        conflicts = [row for row in run["capacity_conflicts"] if row.get("holders")]
        self.assertTrue(conflicts)
        first = conflicts[0]
        self.assertNotIn(first["actor"], first["holders"])

        blocked_node = next(
            node for node in run["topology"]["nodes"] if node["id"] == first["node"]
        )
        self.assertEqual(blocked_node["kind"], "career_option_blocked_by_shared_capacity")
        self.assertTrue(blocked_node["causes"])
        upstream = {
            node["id"]: node for node in run["topology"]["nodes"]
        }
        self.assertTrue(any(
            upstream[cause]["kind"] == "shared_resource_allocated"
            and upstream[cause]["actor"] in first["holders"]
            for cause in blocked_node["causes"]
        ))

    def test_old_characters_pay_time_cost_for_cross_cohort_networking(self):
        run = simulate_career_six_continuity(seed=7)
        self.assertGreater(run["original_core"]["lin_jing"]["time_pressure"], .35)
        self.assertGreater(run["original_core"]["chen_lan"]["time_pressure"], .52)
        self.assertGreater(run["original_core"]["xu_hang"]["time_pressure"], .40)

    def test_job_outcomes_backpropagate_into_original_character_options(self):
        run = simulate_career_six_continuity(seed=23)
        kinds = [node["kind"] for node in run["topology"]["nodes"]]
        self.assertIn("cross_cohort_outcome_backpropagated", kinds)
        self.assertGreater(run["original_core"]["lin_jing"]["public_sector_option"], .20)
        self.assertGreater(run["original_core"]["chen_lan"]["health_data_translation"], .20)
        self.assertGreater(run["original_core"]["xu_hang"]["verification_reputation"], .42)

    def test_2026_target_can_change_after_accumulated_pressure(self):
        runs = [simulate_career_six_continuity(seed=seed) for seed in (1, 7, 23)]
        self.assertTrue(any(
            actor["target_revision_count"] > 0
            for run in runs
            for actor in run["actors"].values()
        ))
        self.assertTrue(any(
            actor["current_target"] != actor["target_2026"]
            for run in runs
            for actor in run["actors"].values()
        ))

    def test_horizon_remains_2026_to_2035(self):
        run = simulate_career_six_continuity(seed=11)
        self.assertEqual([row["year"] for row in run["annual_snapshots"]], list(range(2026, 2036)))
        self.assertEqual(run["status"], "career_six_2026_2035_continuity_v2_noncanonical_scout")


if __name__ == "__main__":
    unittest.main()
