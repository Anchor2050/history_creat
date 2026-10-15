import unittest

from narrative.longform.multiverse import (
    _month_after, run_multiverse, simulate_world, world_specs,
)


class MultiverseTests(unittest.TestCase):
    def test_32_world_plan_has_four_families(self):
        specs = world_specs(32, 7)
        self.assertEqual(len(specs), 32)
        self.assertEqual({s["family"] for s in specs}, {"stable", "macro_shocks", "choice_pressure", "mixed"})
        self.assertEqual(len({s["seed"] for s in specs}), 32)
        self.assertEqual({f: sum(s["family"] == f for s in specs) for f in {s["family"] for s in specs}}, {
            "stable": 8, "macro_shocks": 8, "choice_pressure": 8, "mixed": 8,
        })

    def test_month_offset_is_exact(self):
        self.assertEqual(_month_after("2026-03-01", 0), "2026-03-01")
        self.assertEqual(_month_after("2026-03-01", 9), "2026-12-01")
        self.assertEqual(_month_after("2026-03-01", 10), "2027-01-01")

    def test_seeded_world_is_reproducible(self):
        spec = world_specs(1, 19)[0]
        self.assertEqual(simulate_world(spec, 40), simulate_world(spec, 40))

    def test_stable_has_no_seeded_shock_and_choice_world_keeps_baseline_macro(self):
        specs = world_specs(8, 23)
        stable = next(s for s in specs if s["family"] == "stable")
        choice = next(s for s in specs if s["family"] == "choice_pressure")
        sr = simulate_world(stable, 160)
        cr = simulate_world(choice, 160)
        self.assertFalse(any(isinstance(x.get("provenance"), dict) and x["provenance"].get("kind") == "seeded_exogenous_shock" for x in sr["macro_shocks"]))
        self.assertFalse(any(isinstance(x.get("provenance"), dict) and x["provenance"].get("kind") == "seeded_exogenous_shock" for x in cr["macro_shocks"]))

    def test_160_week_run_finishes_and_only_nominates_choices(self):
        run = simulate_world(world_specs(1, 23)[0], 160)
        self.assertEqual(run["weeks"], 160)
        self.assertEqual(run["status"], "scouting_noncanonical")
        self.assertTrue(run["history"])
        self.assertIn("decision_replay_nodes", run)
        self.assertNotIn("irreversible_proxy_points", run)

    def test_multiverse_returns_pareto_candidates(self):
        result = run_multiverse(8, 24, 31)
        self.assertEqual(len(result["runs"]), 8)
        self.assertLessEqual(len(result["candidates"]), 8)
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["status"], "scouting_noncanonical_requires_deep_replay")


if __name__ == "__main__":
    unittest.main()
