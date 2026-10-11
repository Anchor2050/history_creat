"""No-API StoryBox-like micro replay for the fourteen-person ensemble.

This module keeps the parts of StoryBox that matter for historical simulation:
perception, bounded retrieval, relationship-grounded action, bilateral memory,
and event writeback.  It deliberately does not import Reverie's prompt manager,
LLM module, embedding model, or any external model client.

Two execution modes are supported:
1. ``deterministic``: a seeded pure-Python policy useful for unattended runs and tests;
2. ``external_result``: ChatGPT (this project's existing interactive/automation
   workflow), a human, or a future local model may fill a cognition result packet.
   The packet is validated and then applied without any API call from this repo.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import random


ALLOWED_ACTS = {
    "check_in", "share_experience", "ask_advice", "offer_information",
    "offer_introduction", "offer_help", "decline", "set_boundary",
    "make_plan", "small_talk", "disagree", "repair",
}
REMOTE_CHANNELS = {"phone", "wechat_private", "wechat_group", "email", "video_call"}


@dataclass
class LocalPersona:
    actor_id: str
    scratch: dict
    memories: list[dict] = field(default_factory=list)

    @property
    def name(self):
        return self.scratch.get("name", self.actor_id)

    def remember(self, row):
        self.memories.append(deepcopy(row))

    def retrieve(self, focal_ids, limit=8):
        """Simple auditable retrieval: overlap + recency, no embedding model."""
        focal = {str(x).lower() for x in focal_ids if x}
        scored = []
        for index, row in enumerate(self.memories):
            hay = json.dumps(row, ensure_ascii=False).lower()
            overlap = sum(1 for token in focal if token and token in hay)
            recency = (index + 1) / max(1, len(self.memories))
            scored.append((2.0 * overlap + 0.35 * recency, index, row))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [deepcopy(row) for score, _, row in scored[:limit] if score > 0]


def _event_id(packet_id, suffix):
    digest = hashlib.sha1(f"{packet_id}:{suffix}".encode()).hexdigest()[:12]
    return f"local:{digest}"


def _initial_memories(packet, actor_id, carry_memory=None):
    rows = []
    if carry_memory and actor_id in carry_memory:
        rows.extend(deepcopy(carry_memory[actor_id]))
    seed = packet.get("memory_seeds", {}).get(actor_id, {})
    for relation in seed.get("relationships", []):
        rows.append({
            "kind": "relationship_memory",
            "at": packet["start_date"],
            "about": relation.get("about"),
            "summary": deepcopy(relation),
        })
    rows.append({
        "kind": "window_context",
        "at": packet["start_date"],
        "event_kind": packet["event_kind"],
        "mode": packet["mode"],
        "location": packet["location"],
        "participants": list(packet["participants"]),
    })
    return rows


def load_local_personas(packet, carry_memory=None):
    return {
        actor_id: LocalPersona(
            actor_id=actor_id,
            scratch=deepcopy(packet["persona_seeds"][actor_id]),
            memories=_initial_memories(packet, actor_id, carry_memory),
        )
        for actor_id in packet["participants"]
    }


def _pair_key(a, b):
    return tuple(sorted((a, b)))


def _tie_map(ties):
    return {_pair_key(row["a"], row["b"]): row for row in ties}


def _visible_relationship(actor_id, other_id, ties, packet):
    tie = _tie_map(ties).get(_pair_key(actor_id, other_id))
    if tie:
        return {
            "known": True,
            "kind": tie.get("kind"),
            "trust": tie.get("trust"),
            "closeness": tie.get("closeness"),
            "last_contact": tie.get("last_contact"),
            "introduced_by": tie.get("introduced_by"),
        }
    introduced = any(
        {row.get("a"), row.get("b")} == {actor_id, other_id}
        for row in packet.get("introductions", [])
    )
    return {"known": bool(introduced), "kind": "fresh_introduction" if introduced else None}


def build_cognition_request(packet, ties, carry_memory=None):
    """Build a model-agnostic request.  Nothing here requires an API."""
    personas = load_local_personas(packet, carry_memory)
    actors = {}
    for actor_id, persona in personas.items():
        relations = {}
        for other in packet["participants"]:
            if other == actor_id:
                continue
            relation = _visible_relationship(actor_id, other, ties, packet)
            if relation["known"]:
                relations[other] = relation
        focal = [packet["event_kind"], *relations.keys()]
        actors[actor_id] = {
            "identity": deepcopy(persona.scratch),
            "hard_constraints": deepcopy(packet["hard_constraints"][actor_id]),
            "known_relationships": relations,
            "retrieved_memory": persona.retrieve(focal, limit=10),
        }
    return {
        "request_version": 1,
        "packet_id": packet["id"],
        "start_date": packet["start_date"],
        "event_kind": packet["event_kind"],
        "mode": packet["mode"],
        "location": packet["location"],
        "participants": list(packet["participants"]),
        "actors": actors,
        "allowed_acts": sorted(ALLOWED_ACTS),
        "rules": [
            "use only visible hard state and retrieved/relationship memory",
            "a stranger cannot receive a direct private interaction until introduced",
            "an offer of help is only a promise candidate; it does not alter hard-world resources",
            "remote interaction never changes physical location",
            "do not force every participant to speak",
            "silence, refusal, awkwardness, and ordinary small talk are valid outcomes",
        ],
    }


def _known_pairs(request):
    pairs = []
    for a in request["participants"]:
        for b in request["actors"][a]["known_relationships"]:
            if a < b:
                pairs.append((a, b))
    return sorted(set(pairs))


def _pressure(actor):
    hard = actor.get("hard_constraints", {})
    return float(hard.get("scene_pressure") or 0.45)


def deterministic_replay(request, seed=1, max_interactions=5):
    """Pure-Python fallback. Generates semantic acts, not literary dialogue."""
    rng = random.Random(f"{seed}:{request['packet_id']}")
    pairs = _known_pairs(request)
    rng.shuffle(pairs)
    interactions = []
    for a, b in pairs[:max_interactions]:
        actor_a, actor_b = request["actors"][a], request["actors"][b]
        pa, pb = _pressure(actor_a), _pressure(actor_b)
        rel = actor_a["known_relationships"].get(b, {})
        trust = float(rel.get("trust") or 0.35)
        if max(pa, pb) > 0.78 and trust < 0.55:
            act = rng.choice(["small_talk", "set_boundary", "decline"])
        elif trust > 0.66:
            act = rng.choice(["check_in", "share_experience", "ask_advice", "offer_help"])
        else:
            act = rng.choice(["small_talk", "share_experience", "offer_information", "ask_advice"])
        speaker, listener = (a, b) if rng.random() < 0.5 else (b, a)
        content = {
            "small_talk": "Keeps the exchange ordinary and does not disclose private constraints.",
            "check_in": "Checks how the other person has been doing since their last contact.",
            "share_experience": "Shares a bounded personal or career experience relevant to the current window.",
            "ask_advice": "Asks for perspective without assuming the other person owes help.",
            "offer_information": "Offers information they plausibly possess through their own path.",
            "offer_help": "Offers limited help subject to later feasibility and resource checks.",
            "decline": "Declines or postpones a request because current obligations are too heavy.",
            "set_boundary": "States a boundary around time, money, work, or private information.",
        }[act]
        interactions.append({
            "speaker": speaker,
            "listener": listener,
            "act": act,
            "content": content,
            "channel": request["mode"],
            "evidence": "deterministic_policy",
        })
    return {
        "result_version": 1,
        "packet_id": request["packet_id"],
        "backend": "deterministic_no_api",
        "interactions": interactions,
        "relationship_evidence": [],
        "hard_world_candidates": [
            {
                "type": "promise_candidate",
                "speaker": row["speaker"],
                "listener": row["listener"],
                "source_act": row["act"],
            }
            for row in interactions if row["act"] in {"offer_help", "offer_introduction", "make_plan"}
        ],
    }


def validate_replay_result(request, result):
    if result.get("result_version") != 1 or result.get("packet_id") != request["packet_id"]:
        raise ValueError("replay result does not match request")
    participants = set(request["participants"])
    known = set(_known_pairs(request))
    for row in result.get("interactions", []):
        if row.get("speaker") not in participants or row.get("listener") not in participants:
            raise ValueError("interaction contains unknown participant")
        if row.get("act") not in ALLOWED_ACTS:
            raise ValueError(f"unsupported social act: {row.get('act')}")
        if _pair_key(row["speaker"], row["listener"]) not in known:
            raise ValueError("private interaction attempted without a known/introduction edge")
        if row.get("channel") != request["mode"]:
            raise ValueError("interaction channel differs from scheduled window")
    for row in result.get("relationship_evidence", []):
        if row.get("direction") not in {"positive", "negative", "mixed"}:
            raise ValueError("relationship evidence requires positive/negative/mixed direction")
    return True


def apply_replay_result(packet, ties, request, result, carry_memory=None):
    """Write semantic interactions into bilateral memory and event history.

    Relationship scores are *not* automatically changed by mere conversation.
    The caller may later interpret explicit relationship evidence.
    """
    validate_replay_result(request, result)
    personas = load_local_personas(packet, carry_memory)
    events = []
    for index, row in enumerate(result.get("interactions", []), 1):
        event = {
            "event_id": _event_id(packet["id"], index),
            "kind": "social_interaction",
            "at": packet["start_date"],
            "event_kind": packet["event_kind"],
            **deepcopy(row),
        }
        events.append(event)
        memory = {
            "kind": "interaction_memory",
            "at": packet["start_date"],
            "with": row["listener"],
            "act": row["act"],
            "content": row["content"],
            "event_id": event["event_id"],
        }
        personas[row["speaker"]].remember(memory)
        reverse = deepcopy(memory)
        reverse["with"] = row["speaker"]
        reverse["heard_as_listener"] = True
        personas[row["listener"]].remember(reverse)

    return {
        "status": "storybox_noapi_micro_window_executed_noncanonical",
        "packet_id": packet["id"],
        "backend": result.get("backend", "external_noapi_result"),
        "events": events,
        "persona_memory": {actor_id: deepcopy(p.memories) for actor_id, p in personas.items()},
        "relationship_evidence": deepcopy(result.get("relationship_evidence", [])),
        "hard_world_candidates": deepcopy(result.get("hard_world_candidates", [])),
        "rules": {
            "no_external_api_called": True,
            "conversation_does_not_auto_change_relationship": True,
            "hard_world_candidates_require_separate_feasibility_check": True,
        },
    }


def run_noapi_micro_window(packet, ties, *, carry_memory=None, seed=1, max_interactions=5):
    request = build_cognition_request(packet, ties, carry_memory)
    result = deterministic_replay(request, seed=seed, max_interactions=max_interactions)
    return apply_replay_result(packet, ties, request, result, carry_memory)
