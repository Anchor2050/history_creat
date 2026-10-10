import unittest

from narrative.longform.chat_driver import ChatDriverError, ChatRun
from narrative.longform.scenarios import load_beijing
from narrative.longform.world import World


class PureChatDriverTests(unittest.TestCase):
    def make_run(self):
        return ChatRun("chat-test", World(load_beijing()))

    def reply(self, task, result=None):
        return {"task_id": task["task_id"], "input_hash": task["input_hash"], "state_hash": task["state_hash"],
                "driver": "chatgpt_conversation", "result": result or {"choice": "wait", "reason": "bounded", "actions": []}}

    def test_character_task_does_not_leak_other_private_state(self):
        run = self.make_run()
        task = run.decision_task("lin_jing")
        text = str(task["context"])
        self.assertNotIn("cash_balance", text)
        self.assertNotIn("remaining_affection", text)
        self.assertIn("desire_for_reciprocity", text)

    def test_checkpoint_restores_pending_task_without_api_key(self):
        run = self.make_run(); task = run.decision_task("chen_lan")
        restored = ChatRun.restore(run.checkpoint())
        self.assertEqual(restored.exchange.pending(), task)
        self.assertEqual(restored.state_hash(), run.state_hash())

    def test_stale_reply_is_rejected_after_world_changes(self):
        run = self.make_run(); task = run.decision_task("chen_lan")
        run.world.advance("2026-03-03")
        with self.assertRaises(Exception):
            run.receive(self.reply(task))

    def test_identical_reply_is_idempotent_and_conflict_rejected(self):
        run = self.make_run(); task = run.decision_task("xu_hang"); reply = self.reply(task)
        run.receive(reply); before = run.exchange.snapshot(); run.receive(reply)
        self.assertEqual(run.exchange.snapshot(), before)
        bad = dict(reply); bad["result"] = {"choice": "invent", "reason": "different", "actions": []}
        with self.assertRaises(Exception):
            run.receive(bad)

    def test_receive_is_not_world_acceptance(self):
        run = self.make_run(); task = run.decision_task("xu_hang"); before = run.world.snapshot()
        run.receive(self.reply(task))
        self.assertEqual(run.world.snapshot(), before)
        run.commit_reply({"accepted": False, "reason": "No engine action was applied"})
        self.assertEqual(run.world.snapshot(), before)

    def test_chapter_task_contains_events_and_reader_memory_only(self):
        run = self.make_run()
        run.world.offer_task("offer-1", "gu_wei", "xu_hang", "复核数据版本", 2, "assign_own_group_work")
        task = run.chapter_task([1])
        self.assertEqual(task["context"]["events"][0]["kind"], "task_offered")
        self.assertEqual(task["context"]["reader_memory"]["chapter_summaries"], [])


if __name__ == "__main__":
    unittest.main()
