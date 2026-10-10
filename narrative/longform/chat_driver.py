"""Zero-key chat driver protocol and atomic checkpoint state.

This module never calls a model API. A ChatGPT conversation consumes the pending
minimal task, returns a structured reply, and the engine validates it before the
reply can alter world/character/literary state.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .characters import Characters
from .exchange import Exchange
from .literary import ReaderMemory
from .world import World


class ChatDriverError(ValueError):
    pass


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class ChatRun:
    def __init__(self, run_id, world, characters=None, memory=None, exchange=None):
        self.run_id = run_id
        self.world = world
        self.characters = characters or Characters(world.snapshot()["actors"])
        self.memory = memory or ReaderMemory()
        self.exchange = exchange or Exchange(run_id)
        self.stage = "decisions"
        self.week = 1
        self.driver = "chatgpt_conversation"
        self.audit = []

    def state_hash(self):
        return _digest({"world": self.world.snapshot(), "characters": self.characters.snapshot(),
                        "memory": self.memory.snapshot(), "stage": self.stage, "week": self.week})

    def checkpoint(self):
        return {"version": 1, "run_id": self.run_id, "driver": self.driver, "week": self.week,
                "stage": self.stage, "state_hash": self.state_hash(), "world": self.world.snapshot(),
                "characters": self.characters.snapshot(), "memory": self.memory.snapshot(),
                "exchange": self.exchange.snapshot(), "audit": deepcopy(self.audit)}

    @classmethod
    def restore(cls, snapshot):
        if snapshot.get("version") != 1 or snapshot.get("driver") != "chatgpt_conversation":
            raise ChatDriverError("Unsupported chat checkpoint")
        obj = cls(snapshot["run_id"], World.restore(snapshot["world"]),
                  Characters.restore(snapshot["characters"]), ReaderMemory.restore(snapshot["memory"]),
                  Exchange.restore(snapshot["exchange"]))
        obj.week, obj.stage, obj.audit = snapshot["week"], snapshot["stage"], deepcopy(snapshot["audit"])
        if obj.state_hash() != snapshot["state_hash"]:
            raise ChatDriverError("Checkpoint hash mismatch")
        return obj

    def decision_task(self, actor):
        context = self.characters.visible_context(actor, {
            "story_date": self.world.snapshot()["now"],
            "own_open_tasks": [deepcopy(t) for t in self.world.snapshot()["tasks"].values() if t["assignee"] == actor],
        })
        schema = {"choice": "string", "reason": "string", "actions": "list"}
        return self.exchange.request(f"week-{self.week}:decision:{actor}", self.state_hash(), context,
            "Choose this character's next bounded action from only the supplied knowledge. Do not invent permissions, consent, money, or facts.", schema)

    def receive(self, reply):
        return self.exchange.receive(reply, self.state_hash())

    def commit_reply(self, validation, after_hash=None):
        pending = self.exchange.snapshot()["pending"]
        if not pending or pending["status"] != "received":
            raise ChatDriverError("No received reply")
        before = pending["task"]["state_hash"]
        after_hash = after_hash or self.state_hash()
        record = self.exchange.commit(pending["task"]["task_id"], before, validation, after_hash)
        self.audit.append({"kind": "chat_reply_committed", "task": record["task"]["task_id"],
                           "accepted": validation["accepted"], "before": before, "after": after_hash})
        return record

    def chapter_task(self, selected_event_ids):
        world = self.world.snapshot()
        events = [deepcopy(e) for e in world["events"] if e["id"] in set(selected_event_ids)]
        if len(events) != len(set(selected_event_ids)):
            raise ChatDriverError("Unknown chapter event")
        context = {"chapter_number": len(self.memory.snapshot()["chapters"]) + 1,
                   "events": events, "reader_memory": self.memory.context(),
                   "poetics": "Concrete life, agency, restraint, earned care; never invent world facts to improve the prose."}
        schema = {"title": "string", "text": "string", "summary": "string", "event_ids": "list",
                  "disclosures": "list", "thread_updates": "list", "motif_updates": "list"}
        return self.exchange.request(f"week-{self.week}:chapter", self.state_hash(), context,
            "Write the next continuous Chinese chapter grounded only in selected events and already published reader memory.", schema)

    def review_task(self, draft, literary=False):
        context = {"draft": deepcopy(draft), "available_event_ids": [e["id"] for e in self.world.snapshot()["events"]],
                   "reader_memory": self.memory.context()}
        if literary:
            instruction = "Review voice, concreteness, rhythm/ellipsis, care and agency, and motifs. Cite exact draft snippets and give concrete revisions."
            schema = {"ready": "bool", "axes": "object", "revision_tasks": "list"}
            stage = "literary-review"
        else:
            instruction = "Check every material claim against supplied events and reader memory. Flag invented actions, knowledge, money, permission, consent, or chronology."
            schema = {"supported": "bool", "issues": "list"}
            stage = "fact-review"
        return self.exchange.request(f"week-{self.week}:{stage}", self.state_hash(), context, instruction, schema)

    def publish(self, chapter):
        available = [e["id"] for e in self.world.snapshot()["events"]]
        record = self.memory.publish(chapter, available)
        self.audit.append({"kind": "chapter_published", "number": chapter["number"], "state_hash": self.state_hash()})
        return record
