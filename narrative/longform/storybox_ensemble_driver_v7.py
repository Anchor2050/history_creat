"""Bounded 2026-2035 StoryBox driver for the fourteen-person ensemble.

The long-horizon simulator may produce many candidate social windows. Running an
LLM agent loop for every candidate would be both expensive and narratively noisy.
This driver selects a bounded, coverage-aware subset, executes them in time order
with real Reverie personas, carries memories forward, and records the resulting
contacts as candidate history.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path

from .ensemble_social_replay_v6 import ENSEMBLE_ACTORS, simulate_ensemble_social_replay
from .storybox_micro_runtime_v7 import run_storybox_micro_window


HIGH_VALUE_KINDS = {
    "career_accepted",
    "career_offer_rejected",
    "career_blocked",
    "home_purchase",
    "family_care_pressure",
    "friend_trip",
    "weekend_outing",
    "wedding_or_life_event",
    "cross_school_friend_dinner",
    "alumni_methods_meetup",
    "personal_scene_checkin",
}


def _packet_score(packet, seen_counts):
    score = 0.0
    if packet["event_kind"] in HIGH_VALUE_KINDS:
        score += 2.0
    if packet.get("introductions"):
        score += 2.4 + .4 * len(packet["introductions"])
    if packet["mode"] == "in_person":
        score += .25
    if len(packet["participants"]) >= 4:
        score += .45
    novelty = sum(1.0 / (1 + seen_counts.get(actor, 0)) for actor in packet["participants"])
    score += .55 * novelty
    return score


def select_storybox_windows(packets, *, max_per_year=2, max_total=20):
    """Select costly micro-replays for social coverage and consequential turns."""
    by_year = {}
    for packet in packets:
        year = int(packet["start_date"][:4])
        by_year.setdefault(year, []).append(packet)

    selected = []
    seen_counts = {actor: 0 for actor in ENSEMBLE_ACTORS}
    for year in sorted(by_year):
        pool = list(by_year[year])
        year_selected = []
        while pool and len(year_selected) < max_per_year and len(selected) < max_total:
            pool.sort(
                key=lambda packet: (
                    -_packet_score(packet, seen_counts),
                    packet["start_date"],
                    packet["id"],
                )
            )
            chosen = pool.pop(0)
            year_selected.append(chosen)
            selected.append(chosen)
            for actor in chosen["participants"]:
                seen_counts[actor] = seen_counts.get(actor, 0) + 1
        if len(selected) >= max_total:
            break

    selected.sort(key=lambda packet: (packet["start_date"], packet["id"]))
    return selected


def _tie_index(social_graph):
    return {
        tuple(sorted((tie["a"], tie["b"]))): tie
        for tie in social_graph["ties"]
    }


def apply_storybox_contact_writeback(social_graph, result):
    """Record actual contact without assuming that every conversation improves a tie."""
    ties = _tie_index(social_graph)
    for conversation in result["conversations"]:
        history = conversation.get("chat_history", [])
        if not history:
            continue
        pair = tuple(sorted((history[0][0], history[0][1])))
        tie = ties.get(pair)
        if tie is None:
            continue
        tie["storybox_contact_count"] = tie.get("storybox_contact_count", 0) + 1
        tie["last_storybox_contact"] = result["start_date"]
        tie.setdefault("storybox_event_ids", []).append(conversation["event_id"])
    return social_graph


def _carry_forward(memory_archive, result):
    for actor_id, state in result["persona_state"].items():
        memory_archive[actor_id] = deepcopy(state["long_term_memory"])
    return memory_archive


async def run_storybox_ensemble(
    *,
    seed=7,
    output_dir,
    max_per_year=2,
    max_total=20,
    max_pair_chats=4,
    round_num=3,
):
    """Execute a bounded decade replay with memory continuity across windows."""
    ensemble = simulate_ensemble_social_replay(seed=seed)
    selected = select_storybox_windows(
        ensemble["micro_replay_packets"],
        max_per_year=max_per_year,
        max_total=max_total,
    )
    social_graph = deepcopy(ensemble["social_graph"])
    memory_archive = {}
    results = []
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    for index, packet in enumerate(selected, 1):
        work_dir = root / f"{index:02d}-{packet['start_date']}-{packet['event_kind']}" / "work"
        result_dir = work_dir.parent / "result"
        result = await run_storybox_micro_window(
            packet,
            social_graph["ties"],
            work_dir=work_dir,
            result_dir=result_dir,
            memory_carryover=memory_archive,
            max_pair_chats=max_pair_chats,
            round_num=round_num,
        )
        _carry_forward(memory_archive, result)
        apply_storybox_contact_writeback(social_graph, result)
        results.append(result)

    coverage = {
        actor: sum(actor in row["participants"] for row in results)
        for actor in ENSEMBLE_ACTORS
    }
    candidate_events = [
        {"packet_id": result["packet_id"], "event": event}
        for result in results
        for event in result["events"]
    ]
    final = {
        "status": "storybox_decade_replay_executed_noncanonical",
        "seed": seed,
        "candidate_window_count": len(ensemble["micro_replay_packets"]),
        "executed_window_count": len(results),
        "selected_packet_ids": [packet["id"] for packet in selected],
        "coverage": coverage,
        "storybox_results": results,
        "memory_archive": memory_archive,
        "social_graph_after_storybox": social_graph,
        "candidate_history_events": candidate_events,
        "hard_world_snapshot": ensemble.get("career_world"),
        "rules": [
            "selected windows are expensive micro replays, not automatic canon",
            "memory persists between executed windows",
            "actual dialogue records contact but does not automatically increase trust",
            "hard-world feasibility cannot be overruled by generated dialogue",
            "Storyteller may summarize only after these events exist",
        ],
    }
    (root / "storybox_decade_result.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return final


def main():
    parser = argparse.ArgumentParser(description="Run bounded StoryBox replay for the 14-person ensemble")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output-dir", default="output/storybox-ensemble-v7")
    parser.add_argument("--max-per-year", type=int, default=2)
    parser.add_argument("--max-total", type=int, default=20)
    parser.add_argument("--max-pair-chats", type=int, default=4)
    parser.add_argument("--round-num", type=int, default=3)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for real StoryBox/Reverie dialogue replay")

    result = asyncio.run(run_storybox_ensemble(
        seed=args.seed,
        output_dir=args.output_dir,
        max_per_year=args.max_per_year,
        max_total=args.max_total,
        max_pair_chats=args.max_pair_chats,
        round_num=args.round_num,
    ))
    print(json.dumps({
        "status": result["status"],
        "executed_window_count": result["executed_window_count"],
        "coverage": result["coverage"],
        "result_file": str(Path(args.output_dir) / "storybox_decade_result.json"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
