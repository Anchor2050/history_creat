import unittest

from narrative.longform.ensemble_social_replay_v6 import simulate_ensemble_social_replay
from narrative.longform.storybox_noapi_runtime_v8 import (
    apply_replay_result,
    build_cognition_request,
    deterministic_replay,
    run_noapi_micro_window,
    validate_replay_result,
)
from narrative.longform.storybox_noapi_driver_v8 import (
    run_noapi_decade,
    select_replay_windows,
)


class StoryBoxNoAPIV8Tests(unittest.TestCase):
    def _world_packet(self, seed=7):
        world = simulate_ensemble_social_replay(seed=seed)
        self.assertTrue(world["micro_replay_packets"])
        return world, world["micro_replay_packets"][0]

    def test_runtime_needs_no_external_api(self):
        world, packet = self._world_packet()
        result = run_noapi_micro_window(packet, world["social_graph"]["ties"], seed=7)
        self.assertTrue(result["rules"]["no_external_api_called"])
        self.assertEqual(result["backend"], "deterministic_no_api")

    def test_deterministic_replay_is_reproducible(self):
        world, packet = self._world_packet(seed=11)
        request = build_cognition_request(packet, world["social_graph"]["ties"])
        a = deterministic_replay(request, seed=123)
        b = deterministic_replay(request, seed=123)
        self.assertEqual(a, b)
        self.assertTrue(validate_replay_result(request, a))

    def test_unknown_private_pair_is_rejected(self):
        world, packet = self._world_packet(seed=17)
        request = build_cognition_request(packet, world["social_graph"]["ties"])
        participants = request["participants"]
        strangers = None
        for i, a in enumerate(participants):
            known = set(request["actors"][a]["known_relationships"])
            for b in participants[i + 1:]:
                if b not in known:
                    strangers = (a, b)
                    break
            if strangers:
                break
        if strangers is None:
            self.skipTest("selected packet happens to contain no stranger pair")
        result = {
            "result_version": 1,
            "packet_id": request["packet_id"],
            "backend": "test",
            "interactions": [{
                "speaker": strangers[0], "listener": strangers[1],
                "act": "small_talk", "content": "invalid direct contact",
                "channel": request["mode"],
            }],
            "relationship_evidence": [],
            "hard_world_candidates": [],
        }
        with self.assertRaises(ValueError):
            validate_replay_result(request, result)

    def test_memory_carries_between_windows(self):
        world = simulate_ensemble_social_replay(seed=23)
        packets = select_replay_windows(world, max_per_year=2, total_limit=8)
        carry = {}
        touched = set()
        for index, packet in enumerate(packets):
            request = build_cognition_request(packet, world["social_graph"]["ties"], carry)
            result = deterministic_replay(request, seed=index + 1)
            applied = apply_replay_result(
                packet, world["social_graph"]["ties"], request, result, carry
            )
            for actor_id, rows in applied["persona_memory"].items():
                if actor_id in carry:
                    self.assertGreaterEqual(len(rows), len(carry[actor_id]))
                    touched.add(actor_id)
                carry[actor_id] = rows
        self.assertTrue(touched)

    def test_decade_driver_is_bounded_and_noapi(self):
        result = run_noapi_decade(seed=5, max_per_year=2, total_limit=12)
        self.assertFalse(result["api_required"])
        self.assertEqual(result["backend"], "deterministic_no_api")
        self.assertLessEqual(result["selected_window_count"], 12)
        self.assertTrue(result["rules"]["storybox_protocol_used"])
        self.assertTrue(result["rules"]["external_llm_not_required"])


if __name__ == "__main__":
    unittest.main()
