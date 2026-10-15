import unittest

from narrative.longform.consequence_topology import ConsequenceTopology, TopologyError


class ConsequenceTopologyTests(unittest.TestCase):
    def test_allocation_changes_someone_elses_options(self):
        t = ConsequenceTopology()
        self.assertIn("seek_transition_housing", t.feasible_options("chen_lan"))
        a = t.allocate("university_a.transition_housing", "lin_jing", 1, "2026-06-01")
        self.assertNotIn("seek_transition_housing", t.feasible_options("chen_lan"))
        self.assertEqual(a["kind"], "shared_resource_allocated")

    def test_capacity_cannot_be_overdrawn(self):
        t = ConsequenceTopology()
        t.allocate("university_a.recommendation_slots", "lin_jing", 2, "2026-05-01")
        with self.assertRaises(TopologyError):
            t.allocate("university_a.recommendation_slots", "chen_lan", 1, "2026-05-02")

    def test_causal_trace_keeps_delayed_chain(self):
        t = ConsequenceTopology()
        a = t.allocate("university_a.bridge_funding", "chen_lan", 3000, "2026-06-01")
        b = t.remember("university_a", "chen_bridge_support", True, "2026-06-02", [a["id"]])
        c = t.update_reputation("shen_yan", "chen_lan", "reliability", 0.2,
                                "2027-01-10", [b["id"]])
        trace = t.causal_trace(c["id"])
        self.assertEqual([x["id"] for x in trace], [a["id"], b["id"], c["id"]])

    def test_inactive_actor_loses_material_options(self):
        t = ConsequenceTopology()
        n = t.exit_actor("chen_lan", "2027-07-01", "graduated")
        self.assertEqual(t.feasible_options("chen_lan"), [])
        self.assertEqual(n["kind"], "actor_exited")

    def test_unknown_future_cause_rejected(self):
        t = ConsequenceTopology()
        with self.assertRaises(TopologyError):
            t.remember("university_a", "x", 1, "2026-03-03", ["cause-99999"])


if __name__ == "__main__":
    unittest.main()
