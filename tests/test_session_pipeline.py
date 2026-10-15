import unittest

from narrative.longform.endogenous_world import simulate_endogenous_world
from narrative.longform.session_pipeline import audit_runs, run_session_pipeline
from narrative.longform.story_miner import features, pareto_mine


class StoryMinerTests(unittest.TestCase):
    def test_features_include_rewards_and_penalties(self):
        f = features(simulate_endogenous_world(101, 80))
        self.assertIn("causal_depth", f)
        self.assertIn("coincidence_penalty", f)
        self.assertIn("unsupported_causality_penalty", f)

    def test_miner_does_not_require_scalar_score(self):
        runs = [simulate_endogenous_world(s, 80) for s in (101, 202, 303, 404)]
        chosen = pareto_mine(runs, 3)
        self.assertLessEqual(len(chosen), 3)
        self.assertTrue(all("features" in x and "score" not in x for x in chosen))


class SessionPipelineTests(unittest.TestCase):
    def test_audit_is_explicit(self):
        runs = [simulate_endogenous_world(s, 80) for s in (101, 202)]
        a = audit_runs(runs)
        self.assertEqual(a["worlds"], 2)
        self.assertIn("negative_cash_worlds", a)
        self.assertIn("passes", a)

    def test_small_pipeline_contract(self):
        result = run_session_pipeline(4, 40, 99)
        self.assertEqual(result["world_weeks"], 160)
        self.assertEqual(len(result["runs"]), 4)
        self.assertLessEqual(len(result["candidates"]), 4)
        self.assertIn(result["status"], {"complete_requires_deep_replay", "complete_audit_failed"})


if __name__ == "__main__":
    unittest.main()
