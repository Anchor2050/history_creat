import unittest

from narrative.longform.consequence_topology import ConsequenceTopology
from narrative.longform.scenarios import load_beijing
from narrative.longform.world import World
from narrative.longform.world_social_adapter import (
    WorldSocialAdapter, WorldSocialAdapterError,
)


class WorldSocialAdapterTests(unittest.TestCase):
    def make_adapter(self):
        return WorldSocialAdapter(World(load_beijing()), ConsequenceTopology())

    def test_cash_consequence_uses_world_ledger(self):
        a = self.make_adapter()
        before = a.world.state["ledger"]["accounts"]["chen_lan"]
        a.transfer(
            "social-pay-1", "org:mingheng:project", "chen_lan", 500,
            "bounded paid research work", "2026-03-03",
        )
        self.assertEqual(
            a.world.state["ledger"]["accounts"]["chen_lan"], before + 500
        )

    def test_resource_permission_is_enforced(self):
        a = self.make_adapter()
        with self.assertRaises(WorldSocialAdapterError):
            a.allocate_resource(
                "alloc-1", "university_a.bridge_funding", "chen_lan", 1000,
                "2026-03-03", authority="sun_jie",
                required_permission="allocate_own_project_budget",
            )

    def test_failed_ledger_transfer_rolls_back_topology_and_world(self):
        a = self.make_adapter()
        before = a.snapshot()
        with self.assertRaises(WorldSocialAdapterError):
            a.transfer(
                "too-much", "org:mingheng:project", "chen_lan", 999999,
                "impossible", "2026-03-03",
            )
        self.assertEqual(a.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
