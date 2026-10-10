import unittest

from narrative.longform.multiverse_v2 import run_multiverse_v2, simulate_world_v2
from narrative.longform.multiverse import world_specs


class MultiverseV2Tests(unittest.TestCase):
    def test_32_by_160_shape(self):
        result = run_multiverse_v2(32, 160, 20261011)
        self.assertEqual(result["count"], 32)
        self.assertEqual(result["weeks"], 160)
        self.assertEqual(len(result["runs"]), 32)

    def test_deterministic(self):
        spec = world_specs(1, 20261011)[0]
        self.assertEqual(simulate_world_v2(spec, 160), simulate_world_v2(spec, 160))

    def test_proxy_points_are_explicitly_noncanonical(self):
        result = run_multiverse_v2(8, 160, 20261011)
        for item in result["runs"]:
            for point in item["run"]["proxy_points"]:
                self.assertEqual(point["status"], "proxy_noncanonical")

    def test_delayed_echoes_have_real_delay(self):
        result = run_multiverse_v2(8, 160, 20261011)
        for item in result["runs"]:
            for echo in item["run"]["delayed_echoes"]:
                self.assertGreaterEqual(echo["delay_weeks"], 26)

    def test_frontier_is_subset(self):
        result = run_multiverse_v2(32, 160, 20261011)
        ids = {x["spec"]["world_id"] for x in result["runs"]}
        self.assertTrue(result["pareto_frontier"])
        self.assertTrue(all(x["spec"]["world_id"] in ids for x in result["pareto_frontier"]))


if __name__ == "__main__":
    unittest.main()
