import unittest

from narrative.longform.macro_world import MacroWorld, MacroWorldError, beijing_2026_macro


class MacroWorldTests(unittest.TestCase):
    def make_world(self):
        return MacroWorld(beijing_2026_macro())

    def test_world_moves_without_character_action(self):
        world = self.make_world()
        before = world.state_hash()
        world.advance("2027-03-01")
        self.assertNotEqual(before, world.state_hash())
        self.assertEqual(len(world.snapshot()["events"]), 12)

    def test_same_input_is_deterministic(self):
        a = self.make_world(); b = self.make_world()
        a.advance("2030-01-01"); b.advance("2030-01-01")
        self.assertEqual(a.snapshot(), b.snapshot())

    def test_scheduled_change_is_applied_once_with_provenance(self):
        world = self.make_world()
        world.advance("2028-09-01")
        events = world.snapshot()["events"]
        shocks = [s for e in events for s in e["shocks"]]
        jump = [s for s in shocks if s["change_id"] == "ai-tool-jump-2028"]
        self.assertEqual(len(jump), 1)
        self.assertEqual(jump[0]["provenance"], "fictional_scenario_assumption")
        world.advance("2029-02-01")
        shocks2 = [s for e in world.snapshot()["events"] for s in e["shocks"]]
        self.assertEqual(sum(s["change_id"] == "ai-tool-jump-2028" for s in shocks2), 1)

    def test_actor_pressure_depends_on_exposure(self):
        world = self.make_world()
        world.advance("2030-01-01")
        academic = world.pressures_for({"academic_job_availability": 1.0, "ai_research_capability": 0.2})
        contractor = world.pressures_for({"research_outsourcing_demand": 1.0, "ai_research_capability": 0.2})
        self.assertNotEqual(academic["net_pressure"], contractor["net_pressure"])

    def test_snapshot_round_trip(self):
        world = self.make_world(); world.advance("2028-10-01")
        restored = MacroWorld.restore(world.snapshot())
        self.assertEqual(restored.state_hash(), world.state_hash())

    def test_unknown_signal_rejected(self):
        with self.assertRaises(MacroWorldError):
            self.make_world().pressures_for({"fate": 1.0})


if __name__ == "__main__":
    unittest.main()
