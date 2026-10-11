import unittest

from narrative.longform.ensemble_social_replay_v6 import (
    ENSEMBLE_ACTORS,
    simulate_ensemble_social_replay,
)
from narrative.longform.storybox_micro_runtime_v7 import _merge_memory_seed
from narrative.longform.storybox_ensemble_driver_v7 import (
    apply_storybox_contact_writeback,
    select_storybox_windows,
)


class StoryBoxEnsembleDriverV7Tests(unittest.TestCase):
    def test_window_selection_is_bounded_and_time_ordered(self):
        run = simulate_ensemble_social_replay(seed=7)
        selected = select_storybox_windows(
            run["micro_replay_packets"], max_per_year=2, max_total=20
        )
        self.assertLessEqual(len(selected), 20)
        self.assertEqual(
            selected,
            sorted(selected, key=lambda row: (row["start_date"], row["id"])),
        )
        per_year = {}
        for packet in selected:
            year = packet["start_date"][:4]
            per_year[year] = per_year.get(year, 0) + 1
        self.assertTrue(all(count <= 2 for count in per_year.values()))
        self.assertTrue(set(actor for p in selected for actor in p["participants"]).issubset(set(ENSEMBLE_ACTORS)))

    def test_memory_merge_keeps_prior_chat_and_current_relationship_context(self):
        carry = {
            "event_mem": [],
            "thought_mem": [],
            "chat_mem": [{
                "content": "上次你说年底可能换工作。",
                "memory_type": "chat",
                "create_time": "2027-05-01 08:00 PM",
                "retrieval_cnt": 0,
                "speaker": "a",
                "listener": "b",
            }],
        }
        seed = {
            "event_mem": [],
            "thought_mem": [{
                "content": "Current social window: classmate dinner.",
                "memory_type": "thought",
                "create_time": "2028-02-01 06:30 PM",
                "retrieval_cnt": 0,
            }],
            "chat_mem": [],
        }
        merged = _merge_memory_seed(seed, carry)
        self.assertEqual(len(merged["chat_mem"]), 1)
        self.assertEqual(len(merged["thought_mem"]), 1)
        self.assertIn("年底可能换工作", merged["chat_mem"][0]["content"])
        self.assertIn("Current social window", merged["thought_mem"][0]["content"])

    def test_storybox_contact_writeback_does_not_auto_inflate_trust(self):
        graph = {
            "ties": [{
                "a": "gao_yuan",
                "b": "lin_jing",
                "trust": .61,
                "closeness": .48,
            }]
        }
        result = {
            "start_date": "2028-04-12",
            "conversations": [{
                "event_id": 9,
                "chat_history": [
                    ("gao_yuan", "lin_jing", "最近怎么样？"),
                    ("lin_jing", "gao_yuan", "还行。"),
                ],
            }],
        }
        updated = apply_storybox_contact_writeback(graph, result)
        tie = updated["ties"][0]
        self.assertEqual(tie["trust"], .61)
        self.assertEqual(tie["closeness"], .48)
        self.assertEqual(tie["storybox_contact_count"], 1)
        self.assertEqual(tie["last_storybox_contact"], "2028-04-12")
        self.assertEqual(tie["storybox_event_ids"], [9])


if __name__ == "__main__":
    unittest.main()
