"""Persistent chat-driven StoryBox-like runtime for the fourteen-person ensemble.

This module is designed for the workflow used in this repository today:
ChatGPT itself is the cognition backend.  The repository never calls ChatGPT,
OpenAI, DeepSeek, Ollama, or a local model from this path.

A conversation/automation does four things:
1. read the checkpoint from GitHub;
2. consume its pending cognition task;
3. produce a structured reply using only visible context and retrieved memory;
4. validate/apply the reply and commit the next checkpoint back to GitHub.

The same checkpoint can later be consumed by a DeepSeek API adapter or a local
model adapter because the exchange protocol is driver-neutral.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .exchange import Exchange
from .storybox_noapi_runtime_v8 import apply_replay_result, validate_replay_result


CHECKPOINT_VERSION = 1
DRIVER_NAME = "chatgpt_product_conversation"


def _digest(value):
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _tie_key(row):
    return tuple(sorted((row["a"], row["b"])))


def _merge_persona_memory(carry, applied):
    merged = deepcopy(carry)
    for actor_id, rows in applied["persona_memory"].items():
        merged[actor_id] = deepcopy(rows)
    return merged


class ChatbotReplayRun:
    """Atomic checkpoint for product-chat-driven ensemble replay."""

    def __init__(
        self,
        *,
        run_id,
        social_ties,
        carry_memory=None,
        event_history=None,
        hard_world_candidates=None,
        packet_history=None,
        exchange=None,
        cursor=0,
    ):
        self.run_id = run_id
        self.social_ties = deepcopy(social_ties)
        self.carry_memory = deepcopy(carry_memory or {})
        self.event_history = deepcopy(event_history or [])
        self.hard_world_candidates = deepcopy(hard_world_candidates or [])
        self.packet_history = deepcopy(packet_history or [])
        self.exchange = exchange or Exchange(run_id)
        self.cursor = int(cursor)

    def state_hash(self):
        return _digest({
            "social_ties": self.social_ties,
            "carry_memory": self.carry_memory,
            "event_history": self.event_history,
            "hard_world_candidates": self.hard_world_candidates,
            "packet_history": self.packet_history,
            "cursor": self.cursor,
        })

    def checkpoint(self):
        return {
            "checkpoint_version": CHECKPOINT_VERSION,
            "driver": DRIVER_NAME,
            "run_id": self.run_id,
            "state_hash": self.state_hash(),
            "cursor": self.cursor,
            "social_ties": deepcopy(self.social_ties),
            "carry_memory": deepcopy(self.carry_memory),
            "event_history": deepcopy(self.event_history),
            "hard_world_candidates": deepcopy(self.hard_world_candidates),
            "packet_history": deepcopy(self.packet_history),
            "exchange": self.exchange.snapshot(),
            "rules": {
                "repository_calls_no_model_api": True,
                "chatgpt_product_can_be_cognition_backend": True,
                "future_deepseek_or_local_backend_allowed": True,
                "single_replay_noncanonical": True,
                "hard_world_requires_separate_feasibility": True,
            },
        }

    @classmethod
    def restore(cls, snapshot):
        if snapshot.get("checkpoint_version") != CHECKPOINT_VERSION:
            raise ValueError("unsupported chatbot replay checkpoint")
        if snapshot.get("driver") != DRIVER_NAME:
            raise ValueError("checkpoint belongs to another driver")
        obj = cls(
            run_id=snapshot["run_id"],
            social_ties=snapshot["social_ties"],
            carry_memory=snapshot.get("carry_memory"),
            event_history=snapshot.get("event_history"),
            hard_world_candidates=snapshot.get("hard_world_candidates"),
            packet_history=snapshot.get("packet_history"),
            exchange=Exchange.restore(snapshot["exchange"]),
            cursor=snapshot.get("cursor", 0),
        )
        if obj.state_hash() != snapshot.get("state_hash"):
            raise ValueError("chatbot checkpoint hash mismatch")
        return obj

    def request_window(self, packet, cognition_request):
        """Create or return the one atomic cognition task for this window."""
        if cognition_request.get("packet_id") != packet.get("id"):
            raise ValueError("cognition request and packet differ")
        context = {
            "packet": deepcopy(packet),
            "cognition_request": deepcopy(cognition_request),
            "carry_memory_counts": {
                actor: len(rows) for actor, rows in self.carry_memory.items()
            },
            "recent_events": deepcopy(self.event_history[-12:]),
            "recent_hard_world_candidates": deepcopy(self.hard_world_candidates[-8:]),
        }
        schema = {
            "result_version": 1,
            "packet_id": "must equal cognition_request.packet_id",
            "backend": DRIVER_NAME,
            "interactions": [
                {
                    "speaker": "participant id",
                    "listener": "known/introduction-edge participant id",
                    "act": "one allowed act",
                    "content": "concrete semantic content; dialogue optional",
                    "channel": "scheduled mode",
                    "evidence": "brief reason grounded in visible context/memory",
                }
            ],
            "relationship_evidence": "list; only explicit evidence, never automatic",
            "hard_world_candidates": "list of promises/introductions/plans needing feasibility checks",
        }
        return self.exchange.request(
            stage=f"micro-replay:{packet['id']}",
            state_hash=self.state_hash(),
            context=context,
            instruction=(
                "Act as the cognition layer for this StoryBox-like micro window. "
                "Use only supplied visible hard state, known relationships, and retrieved memories. "
                "Do not invent jobs, money, permissions, meetings, private knowledge, or successful help. "
                "Ordinary conversation, silence, awkwardness, refusal, disagreement, and no major change are valid. "
                "Return structured semantic interactions. Any promise/help/introduction is only a candidate for later hard-world feasibility."
            ),
            output_schema=schema,
        )

    def reply_envelope(self, task, result, *, driver=DRIVER_NAME):
        return {
            "task_id": task["task_id"],
            "input_hash": task["input_hash"],
            "state_hash": task["state_hash"],
            "driver": driver,
            "result": deepcopy(result),
        }

    def receive_and_apply(self, packet, cognition_request, reply):
        """Validate product-chat output, apply memories/events, then atomically commit."""
        before = self.state_hash()
        self.exchange.receive(reply, before)
        result = deepcopy(reply["result"])
        validate_replay_result(cognition_request, result)
        applied = apply_replay_result(
            packet,
            self.social_ties,
            cognition_request,
            result,
            self.carry_memory,
        )
        self.carry_memory = _merge_persona_memory(self.carry_memory, applied)
        self.event_history.extend(deepcopy(applied["events"]))
        self.hard_world_candidates.extend(deepcopy(applied["hard_world_candidates"]))
        self.packet_history.append({
            "packet_id": packet["id"],
            "start_date": packet["start_date"],
            "event_kind": packet["event_kind"],
            "participants": list(packet["participants"]),
            "backend": applied["backend"],
            "event_ids": [row["event_id"] for row in applied["events"]],
        })
        self.cursor += 1
        after = self.state_hash()
        self.exchange.commit(
            task_id=reply["task_id"],
            before_hash=before,
            validation={
                "accepted": True,
                "packet_id": packet["id"],
                "event_count": len(applied["events"]),
                "candidate_count": len(applied["hard_world_candidates"]),
                "relationship_scores_changed": False,
            },
            after_hash=after,
        )
        return applied


def save_checkpoint(snapshot, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_checkpoint(path):
    return ChatbotReplayRun.restore(json.loads(Path(path).read_text(encoding="utf-8")))
