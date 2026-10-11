"""Materialize the chatbot-driven historical ledger without any model call.

The live world is stored as an immutable baseline plus append-only replay batches.
This module merges those files, derives bilateral memories from explicit events,
and tracks candidate/resource state.  It deliberately does not generate dialogue,
change relationship scores, or call an API.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


class LedgerError(ValueError):
    pass


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _append_memory(memory, event):
    speaker = event["speaker"]
    listener = event["listener"]
    common = {
        "at": event["at"],
        "act": event["act"],
        "content": event["content"],
        "event_id": event["event_id"],
    }
    memory.setdefault(speaker, []).append({**common, "with": listener})
    memory.setdefault(listener, []).append(
        {**common, "with": speaker, "heard_as_listener": True}
    )


def _candidate_map(rows):
    return {row["candidate_id"]: deepcopy(row) for row in rows}


def validate_batch(batch):
    if batch.get("schema_version") != 1:
        raise LedgerError("unsupported batch schema")
    event_ids = [row["event_id"] for row in batch.get("events", [])]
    if len(event_ids) != len(set(event_ids)):
        raise LedgerError("duplicate event id inside batch")
    window_ids = [row["packet_id"] for row in batch.get("windows", [])]
    if len(window_ids) != len(set(window_ids)):
        raise LedgerError("duplicate packet id inside batch")
    for row in batch.get("events", []):
        if row.get("speaker") == row.get("listener"):
            raise LedgerError("self interaction is invalid")
        if not all(row.get(k) for k in ("event_id", "at", "speaker", "listener", "act")):
            raise LedgerError("malformed event")
    return True


def materialize_head(head_path):
    """Return one read model from a v2 head and its immutable delta files."""
    head_path = Path(head_path)
    root = head_path.parents[2]
    head = _read(head_path)
    if head.get("schema_version") != 2:
        raise LedgerError("head schema must be v2")

    baseline = _read(root / head["baseline"]["path"])
    state = {
        "run_id": head["run_id"],
        "world_time": baseline["world_time"],
        "cursor": baseline["cursor"],
        "processed_windows": deepcopy(baseline.get("processed_windows", [])),
        "events": deepcopy(baseline.get("event_history", [])),
        "memory": deepcopy(baseline.get("memory_delta", {})),
        "relationship_evidence": deepcopy(baseline.get("relationship_evidence", [])),
        "social_graph_deltas": [],
        "candidate_state": _candidate_map(baseline.get("hard_world_candidates", [])),
        "actor_state_evidence": [],
        "batches": [],
    }

    seen_events = {row["event_id"] for row in state["events"]}
    seen_windows = {row["packet_id"] for row in state["processed_windows"]}

    for rel_path in head["delta_batches"]:
        batch = _read(root / rel_path)
        validate_batch(batch)
        state["batches"].append(batch["batch_id"])

        for row in batch.get("windows", []):
            if row["packet_id"] in seen_windows:
                raise LedgerError(f"duplicate historical window: {row['packet_id']}")
            seen_windows.add(row["packet_id"])
            state["processed_windows"].append(deepcopy(row))

        for row in batch.get("events", []):
            if row["event_id"] in seen_events:
                raise LedgerError(f"duplicate historical event: {row['event_id']}")
            seen_events.add(row["event_id"])
            state["events"].append(deepcopy(row))
            _append_memory(state["memory"], row)

        state["relationship_evidence"].extend(
            deepcopy(batch.get("relationship_evidence", []))
        )
        state["social_graph_deltas"].extend(
            deepcopy(batch.get("social_graph_deltas", []))
        )
        state["actor_state_evidence"].extend(
            deepcopy(batch.get("actor_state_evidence", []))
        )

        for row in batch.get("new_hard_world_candidates", []):
            cid = row["candidate_id"]
            if cid in state["candidate_state"]:
                raise LedgerError(f"candidate already exists: {cid}")
            state["candidate_state"][cid] = deepcopy(row)

        for update in batch.get("hard_world_candidate_updates", []):
            cid = update["candidate_id"]
            if cid not in state["candidate_state"]:
                raise LedgerError(f"candidate update has no source: {cid}")
            state["candidate_state"][cid]["latest_feasibility"] = deepcopy(update)
            state["candidate_state"][cid]["status"] = update["result"]

    state["processed_windows"].sort(key=lambda row: (row["start_date"], row["packet_id"]))
    state["events"].sort(key=lambda row: (row["at"], row["event_id"]))
    state["world_time"] = head["world_time"]
    state["cursor"] = head["cursor"]
    state["next_pending_task"] = deepcopy(head.get("next_pending_task"))
    state["rules"] = deepcopy(head.get("rules", {}))
    return state


def summarize_materialized(state):
    return {
        "world_time": state["world_time"],
        "cursor": state["cursor"],
        "processed_window_count": len(state["processed_windows"]),
        "event_count": len(state["events"]),
        "actors_with_memory": sorted(state["memory"]),
        "relationship_evidence_count": len(state["relationship_evidence"]),
        "new_social_edge_count": len(state["social_graph_deltas"]),
        "candidate_status": {
            cid: row.get("status") for cid, row in sorted(state["candidate_state"].items())
        },
        "next_packet_id": (
            state.get("next_pending_task") or {}
        ).get("packet_id"),
    }
