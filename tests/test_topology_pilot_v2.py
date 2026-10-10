import unittest

from narrative.longform.topology_pilot_v2 import (
    _counterfactual_block,
    run_controlled_world,
    run_four_world_controlled_pilot,
)


class TopologyPilotV2Tests(unittest.TestCase):
    def test_counterfactual_requires_actual_option_loss(self):
        self.assertTrue(_counterfactual_block(1, 0, 1, 1))
        self.assertFalse(_counterfactual_block(2, 0, 1, 1))

    def test_160_week_world_tracks_real_cash(self):
        r = run_controlled_world(101, 160)
        self.assertEqual(r["weeks"], 160)
        self.assertTrue(r["no_negative_cash"])
        self.assertEqual(r["status"], "controlled_pilot_noncanonical")

    def test_acceptance_requires_cross_actor_and_delayed_echo(self):
        result = run_four_world_controlled_pilot()
        self.assertEqual(len(result["worlds"]), 4)
        self.assertTrue(result["acceptance"])
        self.assertTrue(result["accepted_world_ids"])
        for r in result["worlds"]:
            for chain in r["closed_chains"]:
                self.assertGreaterEqual(len(set(chain["actors"])), 2)
                self.assertTrue(chain["counterfactual_verified"])


if __name__ == "__main__":
    unittest.main()
