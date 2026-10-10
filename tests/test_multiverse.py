import unittest

from narrative.longform.multiverse import run_multiverse, simulate_world, world_specs


class MultiverseTests(unittest.TestCase):
    def test_32_world_plan_has_four_families(self):
        specs = world_specs(32, 7)
        self.assertEqual(len(specs), 32)
        self.assertEqual({s["family"] for s in specs}, {"stable", "macro_shocks", "choice_pressure", "mixed"})
        self.assertEqual(len({s["seed"] for s in specs}), 32)

    def test_seeded_world_is_reproducible(self):
        spec = world_specs(1, 19)[0]
        self.assertEqual(simulate_world(spec, 40), simulate_world(spec, 40))

    def test_160_week_run_finishes_and_is_noncanonical(self):
        run = simulate_world(world_specs(1, 23)[0], 160)
        self.assertEqual(run["weeks"], 160)
        self.assertEqual(run["status"], "scouting_noncanonical")
        self.assertTrue(run["history"])

    def test_multiverse_returns_pareto_candidates(self):
        result = run_multiverse(8, 24, 31)
        self.assertEqual(len(result["runs"]), 8)
        self.assertLessEqual(len(result["candidates"]), 8)
        self.assertEqual(result["status"], "scouting_noncanonical_requires_deep_replay")


if __name__ == "__main__":
    unittest.main()
