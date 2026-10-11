import json
import tempfile
import unittest
from pathlib import Path

from narrative.longform.ensemble_social_replay_v6 import simulate_ensemble_social_replay
from narrative.longform.reverie_micro_bridge_v6 import (
    REMOTE_CHANNELS,
    build_replay_plan,
    candidate_pairings,
    materialize_micro_replay,
    validate_micro_packet,
)


class ReverieMicroBridgeV6Tests(unittest.TestCase):
    def _run_and_packet(self, seed=7):
        run = simulate_ensemble_social_replay(seed=seed)
        self.assertTrue(run["micro_replay_packets"])
        return run, run["micro_replay_packets"][0]

    def test_packet_validates(self):
        _, packet = self._run_and_packet()
        self.assertTrue(validate_micro_packet(packet))

    def test_replay_plan_never_selects_unintroduced_stranger_pair(self):
        run, packet = self._run_and_packet(seed=11)
        plan = build_replay_plan(packet, run["social_graph"]["ties"])
        candidates = {
            tuple(sorted((row["a"], row["b"]))): row["reason"]
            for row in candidate_pairings(packet, run["social_graph"]["ties"])
        }
        for row in plan["selected_pair_chats"]:
            key = tuple(sorted((row["a"], row["b"])))
            self.assertNotEqual(candidates[key], "co_present_but_not_introduced")

    def test_materializer_writes_standard_persona_files(self):
        _, packet = self._run_and_packet(seed=17)
        with tempfile.TemporaryDirectory() as tmp:
            root = materialize_micro_replay(packet, tmp)
            self.assertTrue((root / "world.yaml").exists())
            self.assertTrue((root / "micro_packet.json").exists())
            for actor_id in packet["participants"]:
                folder = root / "personas" / actor_id
                self.assertTrue((folder / "scratch.json").exists())
                self.assertTrue((folder / "spatial_memory.json").exists())
                self.assertTrue((folder / "long_term_memory.json").exists())
                scratch = json.loads((folder / "scratch.json").read_text(encoding="utf-8"))
                memory = json.loads((folder / "long_term_memory.json").read_text(encoding="utf-8"))
                self.assertEqual(scratch["name"], packet["persona_seeds"][actor_id]["name"])
                self.assertIn("thought_mem", memory)

    def test_remote_packets_require_no_teleport_contract(self):
        run = simulate_ensemble_social_replay(seed=23)
        remote = [p for p in run["micro_replay_packets"] if p["mode"] in REMOTE_CHANNELS]
        self.assertTrue(remote)
        for packet in remote:
            self.assertTrue(packet["reverie_contract"]["remote_chat_must_not_teleport"])
            self.assertTrue(packet["location"].startswith("digital:"))


if __name__ == "__main__":
    unittest.main()
