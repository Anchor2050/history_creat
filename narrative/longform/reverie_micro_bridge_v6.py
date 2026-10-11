"""Bridge ensemble micro-replay packets into the repository's Reverie machinery.

The original Reverie `chat` function teleports the initiating persona to the
listener. That is unsuitable for decade-scale, multi-city replay. This bridge
reuses Reverie's memory retrieval, relationship summarization, utterance
generation, event manager, and long-term chat memory while keeping the channel
explicit and avoiding physical teleportation for remote contact.
"""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from reverie.manager.datetime_manager import datetime_manager
from reverie.manager.event_manager import event_manager
from reverie.persona.cognitive.retrieve import retrieve
from reverie.persona.cognitive.execute import (
    generate_single_utterance,
    summarize_relationship,
)


REMOTE_CHANNELS = {"phone", "wechat_private", "wechat_group", "email", "video_call"}


def validate_micro_packet(packet):
    required = {
        "packet_version", "id", "start_date", "end_date", "event_kind",
        "mode", "location", "participants", "hard_constraints",
        "persona_seeds", "memory_seeds", "reverie_contract",
    }
    missing = required - set(packet)
    if missing:
        raise ValueError(f"micro replay packet missing: {sorted(missing)}")
    if packet["packet_version"] != 1:
        raise ValueError("unsupported micro replay packet version")
    if len(packet["participants"]) < 2:
        raise ValueError("micro replay needs at least two participants")
    if packet["mode"] in REMOTE_CHANNELS and not packet["reverie_contract"].get(
        "remote_chat_must_not_teleport"
    ):
        raise ValueError("remote replay must explicitly prohibit teleportation")
    return True


def _memory_item(content, memory_type, create_time, **extra):
    row = {
        "content": content,
        "memory_type": memory_type,
        "create_time": create_time,
        "retrieval_cnt": 0,
    }
    row.update(extra)
    return row


def _memory_seed_for_actor(packet, actor_id):
    start = datetime.fromisoformat(packet["start_date"]).strftime("%Y-%m-%d %I:%M %p")
    actor_memory = packet["memory_seeds"][actor_id]
    thought_mem = []
    for row in actor_memory.get("relationships", []):
        statement = (
            f"{row['name']} is known as {row['kind']}; "
            f"trust={row['trust']}, closeness={row['closeness']}, "
            f"contexts={', '.join(row['contexts'])}. "
            f"Last contact={row.get('last_contact') or 'not recorded'}."
        )
        if row.get("introduced_by"):
            statement += f" They were introduced through {row['introduced_by']}."
        thought_mem.append(_memory_item(statement, "thought", start))

    context = actor_memory.get("event_context", {})
    thought_mem.append(
        _memory_item(
            (
                f"Current social window: {context.get('kind')} via "
                f"{context.get('mode')} at {context.get('location')}. "
                "Do not assume information from people you have not met or been told about."
            ),
            "thought",
            start,
        )
    )
    return {"event_mem": [], "thought_mem": thought_mem, "chat_mem": []}


def _world_yaml(packet):
    mode = packet["mode"]
    location = packet["location"]
    description = (
        "A bounded micro-replay venue inside the 2026-2035 ensemble world. "
        "Long-horizon career, money, housing and care constraints are external "
        "hard state and must not be invented away by the scene."
    )
    venue = "Remote Channel" if mode in REMOTE_CHANNELS else "Shared Venue"
    obj = "Communication Endpoint" if mode in REMOTE_CHANNELS else "Table"
    return (
        "name: Ensemble World\n"
        f"description: {description}\n"
        "cities:\n"
        "  - name: Micro City\n"
        "    description: Temporary replay space for one socially plausible window.\n"
        "    places:\n"
        f"      - name: {venue}\n"
        f"        description: Mode={mode}; source_location={location}.\n"
        "        areas:\n"
        "          - name: Shared Space\n"
        "            description: The bounded interaction area for this replay.\n"
        "            objects:\n"
        f"              - name: {obj}\n"
        "                description: A minimal object so spatial memory remains valid.\n"
    )


def _spatial_memory(packet):
    venue = "Remote Channel" if packet["mode"] in REMOTE_CHANNELS else "Shared Venue"
    obj = "Communication Endpoint" if packet["mode"] in REMOTE_CHANNELS else "Table"
    return {
        "Ensemble World": {
            "Micro City": {
                venue: {
                    "Shared Space": [obj]
                }
            }
        }
    }


def materialize_micro_replay(packet, output_dir):
    """Write a Reverie-compatible story directory for one micro window.

    This is intentionally a materializer, not a runner. The caller controls model
    credentials and Config. The generated directory contains world.yaml plus
    standard persona scratch/spatial/long-term memory files.
    """
    validate_micro_packet(packet)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "personas").mkdir(exist_ok=True)
    (root / "world.yaml").write_text(_world_yaml(packet), encoding="utf-8")

    venue = "Remote Channel" if packet["mode"] in REMOTE_CHANNELS else "Shared Venue"
    living_area = f"Ensemble World:Micro City:{venue}:Shared Space"
    spatial = _spatial_memory(packet)
    for actor_id in packet["participants"]:
        persona_dir = root / "personas" / actor_id
        persona_dir.mkdir(parents=True, exist_ok=True)
        scratch = deepcopy(packet["persona_seeds"][actor_id])
        scratch["living_area"] = living_area
        (persona_dir / "scratch.json").write_text(
            json.dumps(scratch, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (persona_dir / "spatial_memory.json").write_text(
            json.dumps(spatial, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (persona_dir / "long_term_memory.json").write_text(
            json.dumps(_memory_seed_for_actor(packet, actor_id), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (root / "micro_packet.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return root


async def channel_chat(
    speaker_persona,
    listener_persona,
    *,
    channel,
    location,
    context,
    round_num=5,
    history_limit=4,
):
    """Run a memory-grounded chat using Reverie cognition without teleportation."""
    if channel not in REMOTE_CHANNELS | {"in_person"}:
        raise ValueError(f"unsupported channel: {channel}")

    chat_history = []
    is_end = False
    for _ in range(round_num):
        for speaker, listener in (
            (speaker_persona, listener_persona),
            (listener_persona, speaker_persona),
        ):
            retrieved = retrieve(speaker, [listener.name], 30)
            relationship = await summarize_relationship(
                speaker, listener, retrieved
            )
            last_chat = "\n".join(
                f"{name}: {utterance}"
                for name, _, utterance in chat_history[-history_limit:]
            )
            focal_points = [listener.name, relationship, context]
            if last_chat:
                focal_points.append(last_chat)
            retrieved = retrieve(speaker, focal_points, 10)
            utterance, is_end = await generate_single_utterance(
                speaker, listener, retrieved, last_chat
            )
            chat_history.append((speaker.name, listener.name, utterance))
            if is_end:
                break
        if is_end:
            break

    speaker_persona.long_term_mem.add_chat_mem(chat_history)
    listener_persona.long_term_mem.add_chat_mem(chat_history)
    event = event_manager.create_event(
        description=(
            f"{speaker_persona.name} is chatting with "
            f"{listener_persona.name} via {channel}"
        ),
        detail=str(chat_history),
        start_time=datetime_manager.get_current_datetime(),
        participants=[speaker_persona.name, listener_persona.name],
        location=location,
    )
    return {
        "event_id": event.event_id,
        "channel": channel,
        "location": location,
        "chat_history": chat_history,
        "teleported": False,
    }


def candidate_pairings(packet, social_graph_ties):
    """Rank plausible pair conversations inside one group event.

    Existing strong ties get some conversations, but introductions and weak ties
    are deliberately surfaced so a dinner/trip can actually change topology.
    """
    validate_micro_packet(packet)
    participants = set(packet["participants"])
    tie_map = {
        tuple(sorted((row["a"], row["b"]))): row
        for row in social_graph_ties
        if row["a"] in participants and row["b"] in participants
    }
    introduced = {
        tuple(sorted((row["a"], row["b"])))
        for row in packet.get("introductions", [])
    }
    candidates = []
    ordered = sorted(participants)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            key = (a, b)
            tie = tie_map.get(key)
            if key in introduced:
                priority = 1.0
                reason = "fresh_introduction"
            elif tie is None:
                priority = .18
                reason = "co_present_but_not_introduced"
            else:
                strength = .55 * tie["trust"] + .45 * tie["closeness"]
                priority = .42 + .38 * (1.0 - abs(strength - .55))
                reason = "existing_tie"
            candidates.append({
                "a": a, "b": b,
                "priority": round(priority, 4),
                "reason": reason,
            })
    candidates.sort(key=lambda row: (-row["priority"], row["a"], row["b"]))
    return candidates


def build_replay_plan(packet, social_graph_ties, max_pair_chats=4):
    """Create a bounded interaction plan for a StoryBox micro window."""
    pairings = candidate_pairings(packet, social_graph_ties)
    selected = [
        row for row in pairings
        if row["reason"] != "co_present_but_not_introduced"
    ][:max_pair_chats]
    return {
        "packet_id": packet["id"],
        "mode": packet["mode"],
        "location": packet["location"],
        "selected_pair_chats": selected,
        "group_event_context": (
            f"{packet['event_kind']} involving "
            + ", ".join(packet["participants"])
        ),
        "rules": [
            "reuse each persona's existing memory before generating dialogue",
            "do not expose private information absent from memory",
            "remote contact does not change physical location",
            "in-person contact is allowed only because the scheduler already established co-presence",
            "write resulting chat to both personas' long-term memories",
            "write resulting interaction as an event before Storyteller summarizes it",
        ],
    }
