"""Default decade driver for StoryBox-like replay without any external API.

The historical world first produces socially plausible micro windows.  This
driver then executes a bounded subset using ``storybox_noapi_runtime_v8``.
The default backend is deterministic and fully local.  Interactive ChatGPT or a
scheduled ChatGPT task can instead consume the same cognition request and write
an external result packet back through the same validator/apply path.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path

from .ensemble_social_replay_v6 import simulate_ensemble_social_replay
from .storybox_noapi_runtime_v8 import (
    apply_replay_result,
    build_cognition_request,
    deterministic_replay,
)


def _packet_year(packet):
    return int(packet["start_date"][:4])


def select_replay_windows(run, *, max_per_year=2, total_limit=20):
    """Select a sparse decade sample; ordinary life stays mostly macro-scale."""
    packets = sorted(run["micro_replay_packets"], key=lambda row: (row["start_date"], row["id"]))
    selected = []
    yearly = {}
    seen_actors = set()

    # First pass: favour windows that cover people not yet seen that year.
    for packet in packets:
        year = _packet_year(packet)
        if yearly.get(year, 0) >= max_per_year:
            continue
        novelty = len(set(packet["participants"]) - seen_actors)
        turning_point = packet["event_kind"] in {
            "recruitment_information_session", "project_meal",
            "friend_trip", "weekend_outing", "wedding_or_life_event",
            "personal_scene_checkin",
        }
        if novelty or turning_point:
            selected.append(packet)
            yearly[year] = yearly.get(year, 0) + 1
            seen_actors.update(packet["participants"])
        if len(selected) >= total_limit:
            return selected

    # Second pass fills under-covered years without exceeding caps.
    selected_ids = {row["id"] for row in selected}
    for packet in packets:
        if packet["id"] in selected_ids:
            continue
        year = _packet_year(packet)
        if yearly.get(year, 0) >= max_per_year:
            continue
        selected.append(packet)
        yearly[year] = yearly.get(year, 0) + 1
        if len(selected) >= total_limit:
            break
    return sorted(selected, key=lambda row: (row["start_date"], row["id"]))


def _merge_actor_memory(carry, window_result):
    for actor_id, rows in window_result["persona_memory"].items():
        carry[actor_id] = deepcopy(rows)
    return carry


def run_noapi_decade(
    *,
    seed=1,
    max_per_year=2,
    total_limit=20,
    max_interactions=5,
):
    """Run the selected 2026-2035 windows with no API and no model service."""
    world = simulate_ensemble_social_replay(seed=seed)
    ties = deepcopy(world["social_graph"]["ties"])
    selected = select_replay_windows(
        world, max_per_year=max_per_year, total_limit=total_limit
    )
    carry = {}
    windows = []
    history_events = []

    for index, packet in enumerate(selected):
        request = build_cognition_request(packet, ties, carry)
        replay = deterministic_replay(
            request,
            seed=seed * 1000 + index,
            max_interactions=max_interactions,
        )
        applied = apply_replay_result(packet, ties, request, replay, carry)
        _merge_actor_memory(carry, applied)
        history_events.extend(applied["events"])
        windows.append({
            "packet_id": packet["id"],
            "start_date": packet["start_date"],
            "event_kind": packet["event_kind"],
            "participants": list(packet["participants"]),
            "backend": applied["backend"],
            "events": deepcopy(applied["events"]),
            "hard_world_candidates": deepcopy(applied["hard_world_candidates"]),
        })

    return {
        "status": "storybox_noapi_decade_replay_noncanonical",
        "seed": seed,
        "backend": "deterministic_no_api",
        "api_required": False,
        "selected_window_count": len(selected),
        "selected_windows": windows,
        "event_history": history_events,
        "carry_memory": carry,
        "base_social_graph": deepcopy(world["social_graph"]),
        "rules": {
            "storybox_protocol_used": True,
            "external_llm_not_required": True,
            "literary_dialogue_not_claimed": True,
            "single_run_not_canonical": True,
        },
    }


def prepare_next_chatgpt_replay(packet, ties, carry_memory=None):
    """Produce the request an interactive/scheduled ChatGPT run can answer.

    This is still no-API from the repository's perspective: ChatGPT receives the
    request through the existing product conversation/automation and returns a
    structured result that can be validated by ``apply_chatgpt_replay``.
    """
    return build_cognition_request(packet, ties, carry_memory)


def apply_chatgpt_replay(packet, ties, cognition_request, chatgpt_result, carry_memory=None):
    result = deepcopy(chatgpt_result)
    result.setdefault("backend", "chatgpt_product_no_external_api")
    return apply_replay_result(
        packet, ties, cognition_request, result, carry_memory
    )


def save_decade_result(result, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
