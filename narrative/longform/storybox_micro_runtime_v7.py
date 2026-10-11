"""Execute ensemble micro-windows with the repository's Reverie personas.

The long-horizon world decides which social windows are feasible. This runtime
hands a bounded window to real Reverie Persona objects, lets them perceive,
retrieve and converse, and exports memory/events for later windows.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import ast
import json
from pathlib import Path

from reverie.common.event import Event
from reverie.database.database import db
from reverie.database.table.persona_table import PersonaTable
from reverie.environment.world import World
from reverie.manager.datetime_manager import datetime_manager
from reverie.manager.event_manager import event_manager
from reverie.manager.persona_manager import persona_manager
from reverie.persona.persona import Persona

from .reverie_micro_bridge_v6 import (
    REMOTE_CHANNELS,
    build_replay_plan,
    channel_chat,
    materialize_micro_replay,
    validate_micro_packet,
)


def _scene_start(packet):
    day = datetime.fromisoformat(packet["start_date"])
    if packet["event_kind"] in {"recruiting_event", "methods_event", "project_meal"}:
        hour = 14
    elif packet["mode"] in REMOTE_CHANNELS:
        hour = 20
    else:
        hour = 18
    return day.replace(hour=hour, minute=30, second=0, microsecond=0)


def reset_reverie_runtime():
    """Clear singleton DB state before one isolated micro-window."""
    db.query(PersonaTable).delete()
    db.query(Event).delete()
    db.commit()
    persona_manager._persona_dict.clear()


def _merge_memory_seed(seed, carry):
    """Carry prior StoryBox memory while adding current-window relationship facts."""
    if not carry:
        return seed
    merged = {
        "event_mem": deepcopy(carry.get("event_mem", [])),
        "thought_mem": deepcopy(carry.get("thought_mem", [])),
        "chat_mem": deepcopy(carry.get("chat_mem", [])),
    }
    fingerprints = {
        (row.get("memory_type"), row.get("content"), row.get("create_time"))
        for rows in merged.values() for row in rows
    }
    for bucket in ("event_mem", "thought_mem", "chat_mem"):
        for row in seed.get(bucket, []):
            fp = (row.get("memory_type"), row.get("content"), row.get("create_time"))
            if fp not in fingerprints:
                merged[bucket].append(deepcopy(row))
                fingerprints.add(fp)
    return merged


def load_micro_world(packet, work_dir, memory_carryover=None):
    """Materialize and load one packet into real Reverie World/Persona classes."""
    validate_micro_packet(packet)
    root = materialize_micro_replay(packet, work_dir)
    memory_carryover = memory_carryover or {}
    for actor_id in packet["participants"]:
        memory_file = root / "personas" / actor_id / "long_term_memory.json"
        current_seed = json.loads(memory_file.read_text(encoding="utf-8"))
        merged = _merge_memory_seed(current_seed, memory_carryover.get(actor_id))
        memory_file.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    reset_reverie_runtime()
    datetime_manager.set_current_datetime(_scene_start(packet))

    world = World()
    if not world.load_file(str(root / "world.yaml")):
        raise RuntimeError("failed to load generated micro world")

    personas = {}
    for actor_id in packet["participants"]:
        folder = root / "personas" / actor_id
        persona = Persona(actor_id, str(folder))
        persona_manager.add_persona(persona)
        personas[actor_id] = persona
    return root, world, personas


def _kickoff_event(packet):
    venue = (
        "Ensemble World:Micro City:Remote Channel:Shared Space"
        if packet["mode"] in REMOTE_CHANNELS
        else "Ensemble World:Micro City:Shared Venue:Shared Space"
    )
    event = event_manager.create_event(
        description=f"Micro social window: {packet['event_kind']}",
        detail=json.dumps(
            {
                "packet_id": packet["id"],
                "mode": packet["mode"],
                "hard_constraints": packet["hard_constraints"],
                "introductions": packet.get("introductions", []),
            },
            ensure_ascii=False,
        ),
        start_time=datetime_manager.get_current_datetime(),
        duration=timedelta(hours=2),
        participants=packet["participants"],
        location=venue,
    )
    return event, venue


def perceive_window(personas, world):
    """Use real Persona.perceive/retrieve before or after dialogue."""
    rows = {}
    for actor_id, persona in personas.items():
        perceived = persona.perceive(world)
        retrieved = persona.retrieve(perceived) if perceived else {}
        rows[actor_id] = {
            "perceived_event_ids": [event.event_id for event in perceived],
            "retrieved_keys": [str(key) for key in retrieved.keys()],
        }
    return rows


def _event_to_row(event):
    detail = event.detail
    if detail and isinstance(detail, str):
        try:
            detail = ast.literal_eval(detail)
        except (ValueError, SyntaxError):
            pass
    return {
        "event_id": event.event_id,
        "description": event.description,
        "detail": detail,
        "start_time": event.start_time.isoformat() if event.start_time else None,
        "end_time": event.end_time.isoformat() if event.end_time else None,
        "duration": event.duration,
        "participants": deepcopy(event.participants),
        "location": event.location,
    }


def export_persona_state(persona):
    return {
        "scratch": {
            "name": persona.scratch.name,
            "age": persona.scratch.age,
            "innate": persona.scratch.innate,
            "learned": persona.scratch.learned,
            "currently": persona.scratch.currently,
            "lifestyle": persona.scratch.lifestyle,
            "living_area": persona.scratch.living_area,
            "daily_plan_requirement": deepcopy(persona.scratch.daily_plan_requirement),
        },
        "long_term_memory": {
            "event_mem": [item.to_dict() for item in persona.long_term_mem.event_mem],
            "thought_mem": [item.to_dict() for item in persona.long_term_mem.thought_mem],
            "chat_mem": [item.to_dict() for item in persona.long_term_mem.chat_mem],
        },
    }


def save_persona_state(personas, output_dir):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    exports = {}
    for actor_id, persona in personas.items():
        actor_dir = root / actor_id
        actor_dir.mkdir(parents=True, exist_ok=True)
        persona.save(str(actor_dir))
        persona.long_term_mem.save(str(actor_dir / "long_term_memory.json"))
        exports[actor_id] = export_persona_state(persona)
    return exports


async def run_storybox_micro_window(
    packet,
    social_graph_ties,
    *,
    work_dir,
    result_dir=None,
    memory_carryover=None,
    max_pair_chats=4,
    round_num=3,
):
    """Run one bounded StoryBox/Reverie scene with real Persona objects."""
    root, world, personas = load_micro_world(
        packet, work_dir, memory_carryover=memory_carryover
    )
    kickoff, venue = _kickoff_event(packet)
    perception = perceive_window(personas, world)
    plan = build_replay_plan(packet, social_graph_ties, max_pair_chats=max_pair_chats)

    conversations = []
    for row in plan["selected_pair_chats"]:
        a, b = row["a"], row["b"]
        result = await channel_chat(
            personas[a],
            personas[b],
            channel=packet["mode"],
            location=venue,
            context=(
                f"{plan['group_event_context']}. Pairing reason={row['reason']}. "
                f"Hard constraints={packet['hard_constraints']}"
            ),
            round_num=round_num,
        )
        result["pairing_reason"] = row["reason"]
        conversations.append(result)

    post_perception = perceive_window(personas, world)
    if result_dir is None:
        result_dir = Path(root) / "result"
    exported = save_persona_state(personas, result_dir)
    events = [_event_to_row(event) for event in event_manager.get_all_events()]

    return {
        "status": "storybox_micro_window_executed_noncanonical",
        "packet_id": packet["id"],
        "start_date": packet["start_date"],
        "event_kind": packet["event_kind"],
        "mode": packet["mode"],
        "participants": list(packet["participants"]),
        "kickoff_event_id": kickoff.event_id,
        "pre_dialogue_perception": perception,
        "replay_plan": plan,
        "conversations": conversations,
        "post_dialogue_perception": post_perception,
        "events": events,
        "persona_state": exported,
        "writeback_contract": {
            "event_rows_are_candidate_history": True,
            "persona_memory_must_carry_into_later_windows": True,
            "dialogue_does_not_override_hard_world": True,
            "single_window_is_not_canonical": True,
        },
    }
