import unittest

from narrative.longform.endogenous_world import _external_schedule, simulate_endogenous_world


class EndogenousWorldTests(unittest.TestCase):
    def test_external_schedule_replays_exactly(self):
        self.assertEqual(_external_schedule(17, 160), _external_schedule(17, 160))
        self.assertNotEqual(_external_schedule(17, 160), _external_schedule(18, 160))
        self.assertTrue(all(e["provenance"]["kind"] == "seeded_exogenous_event" for e in _external_schedule(17, 160)))

    def test_same_seed_same_world(self):
        self.assertEqual(simulate_endogenous_world(41, 80), simulate_endogenous_world(41, 80))

    def test_160_weeks_has_lifecycle_and_auditable_causality(self):
        run = simulate_endogenous_world(101, 160)
        self.assertEqual(run["weeks"], 160)
        self.assertEqual(run["status"], "endogenous_scouting_noncanonical")
        self.assertTrue(run["lifecycle"])
        for chain in run["cross_actor_chains"]:
            self.assertNotIn(chain["blocked_actor"], chain["holder_actors"])
            self.assertGreaterEqual(chain["trace_length"], 2)

    def test_cash_path_is_reported_not_hidden(self):
        run = simulate_endogenous_world(202, 160)
        self.assertEqual(set(run["minimum_cash_seen"]), {"lin_jing", "chen_lan", "xu_hang"})
        self.assertIsInstance(run["no_negative_cash"], bool)


if __name__ == "__main__":
    unittest.main()
