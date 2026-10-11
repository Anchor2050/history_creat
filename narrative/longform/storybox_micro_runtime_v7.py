"""Execute one ensemble micro-window with the repository's Reverie personas.

This is the point where the long-horizon social-physics layer hands control to
StoryBox/Reverie-style agents. The scheduler decides who can plausibly be in the
same window; this runtime lets those personas perceive, retrieve, converse, and
store memories before exporting the results back to the long-horizon world.
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
    """Choose a human-scale start time inside the already-approved social window."""
    day = datetime.fromisoformat(packet["start_date"])
    if packet["event_kind"] in {"recruiting_event", "methods_event", "project_meal"}:
        hour = 14
    elif packet["mode"] in REMOTE_CHANNELS:
        hour = 20
    else:
        hour = 18
    return day.replace(hour=hour, minute=30, second=0, microsecond=0)


def reset_reverie_runtime():
    """Clear the singleton DB-backed runtime before loading one isolated window."""
    db.query(PersonaTable).delete()
    db.query(Event).delete()
    db.commit()
    persona_manager._persona_dict.clear()


def load_micro_world(packet, work_dir):
    """Materialize and load a packet into the actual Reverie World/Persona classes."""
    validate_micro_packet(packet)
    root = materialize_micro_replay(packet, work_dir)
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
    """Create the shared social fact each persona is allowed to perceive."""
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
    """Use real Persona.perceive/retrieve before any dialogue is generated."""
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
            parsed = ast.literal_eval(detail)
            detail = parsed
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
    """Return the memory state that the long-horizon engine must carry forward."""
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
    max_pair_chats=4,
    round_num=3,
):
    """Run one bounded StoryBox-like scene with actual repository personas.

    No dialogue is prewritten here. The long-horizon layer only supplies legal
    co-presence, hard constraints, memory seeds, and relationship paths. Reverie
    then supplies perception, retrieval, relationship-grounded utterances, and
    bilateral long-term chat memory.
    """
    root, world, personas = load_micro_world(packet, work_dir)
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

    # Let each persona perceive the conversations/events that now exist in the
    # micro world. This is what turns a scene into future retrievable memory.
    post_perception = perceive_window(personas, world)

    if result_dir is None:
        result_dir = Path(root) / "result"
    exported = save_persona_state(personas, result_dir)
    events = [_event_to_row(event) for event in event_manager.get_all_events()]

    return {
        "status": "storybox_micro_window_executed_noncanonical",
        "packet_id": packet["id"],
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
