import unittest
from pathlib import Path

from narrative.longform.storybox_chatbot_ledger_v10 import (
    materialize_head,
    summarize_materialized,
)


class StoryboxChatbotLedgerV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.state = materialize_head(
            cls.root / "runtime" / "chatbot-live" / "head-v2.json"
        )
        cls.summary = summarize_materialized(cls.state)

    def test_2026_head_counts(self):
        self.assertEqual(self.summary["world_time"], "2026-12-31")
        self.assertEqual(self.summary["processed_window_count"], 20)
        self.assertEqual(self.summary["event_count"], 67)

    def test_all_fourteen_actors_have_memory(self):
        expected = {
            "lin_jing", "chen_lan", "xu_hang", "wu_cheng",
            "shen_yan", "gu_wei", "zhao_ke", "sun_jie",
            "zhou_ye", "gao_yuan", "luo_cheng",
            "tang_yu", "he_xin", "song_nan",
        }
        self.assertEqual(set(self.summary["actors_with_memory"]), expected)

    def test_candidates_can_succeed_or_fail(self):
        status = self.summary["candidate_status"]
        self.assertEqual(
            status["candidate:2026-06-13:zhao-song-scoped-health-data-trial:01"],
            "closed_no_matching_need_noncanonical",
        )
        self.assertEqual(
            status["candidate:2026-05-10:shen-review-tang-problem-tree:01"],
            "activated_once_noncanonical",
        )
        self.assertEqual(
            status["candidate:2026-06-27:xu-review-zhou-repro-pack:01"],
            "activated_once_noncanonical",
        )

    def test_only_explicit_introductions_add_edges(self):
        edges = {
            tuple(sorted((row["a"], row["b"])))
            for row in self.state["social_graph_deltas"]
        }
        self.assertEqual(
            edges,
            {
                ("song_nan", "xu_hang"),
                ("he_xin", "luo_cheng"),
                ("tang_yu", "zhou_ye"),
            },
        )

    def test_next_window_enters_2027_without_prewriting_result(self):
        task = self.state["next_pending_task"]
        self.assertEqual(task["start_date"], "2027-01-15")
        self.assertEqual(task["participants"], ["tang_yu", "xu_hang"])
        self.assertEqual(task["event_kind"], "verification_collaboration")


if __name__ == "__main__":
    unittest.main()
