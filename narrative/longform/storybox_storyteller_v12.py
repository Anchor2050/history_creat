"""Evidence-graph Storyteller for the chatbot-led long history.

Storyteller v12 is a read-only historical observer. It never creates or edits
world facts. It turns append-only replay batches into an auditable narrative
index so later literary work can discover long arcs without inventing them.

The layer deliberately separates three things:

1. ledger facts: events, candidate lifecycles, state evidence, introductions;
2. deterministic indices: timelines, delayed consequences, unresolved threads,
   scene clusters and viewpoint coverage; and
3. interpretive Storyteller output produced by a cognition backend, where every
   claim must cite ledger evidence.

Literary prose generation remains disabled here.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any, Iterable, Mapping

from .storybox_cognition_protocol_v11 import (
    CognitionProtocolError,
    build_task,
    validate_common_result,
)


FAILURE_TOKENS = (
    "reject", "rejected", "closed", "no_offer", "below_cutoff", "refuted",
    "failed", "not_selected", "false", "declined", "withdrawn", "cancelled",
)
SUCCESS_TOKENS = (
    "accepted", "activated", "completed", "selected", "offer_accepted",
    "passed", "adopted", "submitted", "started", "resolved",
)
ORDINARY_ACTS = {"small_talk", "check_in", "repair"}


def _date(row: Mapping[str, Any]) -> str:
    return str(row.get("at") or row.get("created_at") or row.get("checked_at") or "")


def _ref(prefix: str, batch_id: str, index: int, row: Mapping[str, Any]) -> str:
    for key in ("event_id", "candidate_id", "evidence_id"):
        if row.get(key):
            return str(row[key])
    return f"{prefix}:{batch_id}:{index:03d}"


def build_evidence_graph(batches: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Materialize a read-only evidence graph from replay batches.

    Nodes are ledger facts. Edges express only mechanically supported links:
    same candidate id, explicit speaker/listener participation, explicit
    introduction and chronological succession within one actor's owned state.
    No psychological or causal interpretation is added here.
    """
    batches = list(batches)
    nodes: list[dict[str, Any]] = []
    candidate_creations: dict[str, str] = {}
    candidate_updates: defaultdict[str, list[str]] = defaultdict(list)
    actor_refs: defaultdict[str, list[str]] = defaultdict(list)
    pair_refs: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    introduction_refs: list[str] = []

    def add_node(kind: str, batch_id: str, index: int, row: Mapping[str, Any], *, actors=(), pair=None):
        ref = _ref(kind, batch_id, index, row)
        node = {
            "ref": ref,
            "kind": kind,
            "batch_id": batch_id,
            "at": _date(row),
            "actors": sorted({str(a) for a in actors if a}),
            "payload": deepcopy(dict(row)),
        }
        nodes.append(node)
        for actor in node["actors"]:
            actor_refs[actor].append(ref)
        if pair and all(pair):
            key = tuple(sorted((str(pair[0]), str(pair[1]))))
            pair_refs[key].append(ref)
        return ref

    for batch in batches:
        batch_id = str(batch.get("batch_id") or "unknown_batch")
        for i, row in enumerate(batch.get("events", []), 1):
            speaker, listener = row.get("speaker"), row.get("listener")
            actors = [a for a in (speaker, listener) if a and a != "self_record"]
            add_node("social_event", batch_id, i, row, actors=actors, pair=(speaker, listener))

        for i, row in enumerate(batch.get("exogenous_hard_world_events", []), 1):
            add_node("owned_hard_world_event", batch_id, i, row, actors=[row.get("actor")])

        for i, row in enumerate(batch.get("new_hard_world_candidates", []), 1):
            actors = [row.get("beneficiary"), row.get("proposer")]
            ref = add_node("candidate_created", batch_id, i, row, actors=actors)
            if row.get("candidate_id"):
                candidate_creations[str(row["candidate_id"])] = ref

        for i, row in enumerate(batch.get("hard_world_candidate_updates", []), 1):
            actors = [row.get("actor"), row.get("beneficiary"), row.get("proposer")]
            ref = add_node("candidate_updated", batch_id, i, row, actors=actors)
            if row.get("candidate_id"):
                candidate_updates[str(row["candidate_id"])].append(ref)

        for i, row in enumerate(batch.get("actor_state_evidence", []), 1):
            add_node("actor_state_evidence", batch_id, i, row, actors=[row.get("actor")])

        for i, row in enumerate(batch.get("social_graph_deltas", []), 1):
            actors = [row.get("a"), row.get("b"), row.get("introduced_by")]
            ref = add_node("social_graph_delta", batch_id, i, row, actors=actors, pair=(row.get("a"), row.get("b")))
            if row.get("kind") == "introduction":
                introduction_refs.append(ref)

    nodes.sort(key=lambda row: (row.get("at") or "", row["ref"]))
    by_ref = {row["ref"]: row for row in nodes}

    edges: list[dict[str, Any]] = []
    # Candidate lifecycle edges are strong mechanical links.
    for candidate_id, created_ref in candidate_creations.items():
        previous = created_ref
        for updated_ref in candidate_updates.get(candidate_id, []):
            edges.append({
                "kind": "candidate_lifecycle",
                "from": previous,
                "to": updated_ref,
                "candidate_id": candidate_id,
            })
            previous = updated_ref

    # Actor continuity edges only mean chronology, not causation.
    for actor, refs in actor_refs.items():
        ordered = sorted(refs, key=lambda ref: (by_ref[ref].get("at") or "", ref))
        for left, right in zip(ordered, ordered[1:]):
            edges.append({"kind": "actor_chronology", "from": left, "to": right, "actor": actor})

    return {
        "nodes": nodes,
        "edges": edges,
        "actor_refs": {k: v for k, v in actor_refs.items()},
        "pair_refs": {"|".join(k): v for k, v in pair_refs.items()},
        "candidate_creations": candidate_creations,
        "candidate_updates": {k: v for k, v in candidate_updates.items()},
        "introduction_refs": introduction_refs,
    }


def actor_timelines(graph: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_ref = {row["ref"]: row for row in graph.get("nodes", [])}
    result: dict[str, list[dict[str, Any]]] = {}
    for actor, refs in graph.get("actor_refs", {}).items():
        rows = [by_ref[ref] for ref in refs if ref in by_ref]
        rows.sort(key=lambda row: (row.get("at") or "", row["ref"]))
        result[actor] = [
            {"ref": row["ref"], "at": row.get("at"), "kind": row.get("kind"), "payload": row.get("payload")}
            for row in rows
        ]
    return result


def candidate_lifecycles(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_ref = {row["ref"]: row for row in graph.get("nodes", [])}
    rows = []
    candidate_ids = set(graph.get("candidate_creations", {})) | set(graph.get("candidate_updates", {}))
    for candidate_id in sorted(candidate_ids):
        refs = []
        created = graph.get("candidate_creations", {}).get(candidate_id)
        if created:
            refs.append(created)
        refs.extend(graph.get("candidate_updates", {}).get(candidate_id, []))
        refs = [ref for ref in refs if ref in by_ref]
        refs.sort(key=lambda ref: (by_ref[ref].get("at") or "", ref))
        statuses = []
        for ref in refs:
            payload = by_ref[ref].get("payload", {})
            value = payload.get("result") or payload.get("status") or ""
            if value:
                statuses.append(str(value))
        final = statuses[-1].lower() if statuses else ""
        if any(token in final for token in FAILURE_TOKENS):
            outcome = "closed_or_failed"
        elif any(token in final for token in SUCCESS_TOKENS):
            outcome = "activated_or_successful"
        else:
            outcome = "open_or_ambiguous"
        rows.append({
            "candidate_id": candidate_id,
            "refs": refs,
            "statuses": statuses,
            "outcome": outcome,
        })
    return rows


def unresolved_threads(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    threads = []
    for lifecycle in candidate_lifecycles(graph):
        if lifecycle["outcome"] == "open_or_ambiguous":
            threads.append({
                "kind": "candidate",
                "thread_id": lifecycle["candidate_id"],
                "evidence_refs": lifecycle["refs"],
                "reason": "candidate lifecycle has no documented terminal resolution",
            })
    return threads


def delayed_consequence_candidates(graph: Mapping[str, Any], *, min_days_proxy: int = 2) -> list[dict[str, Any]]:
    """Find long candidate lifecycles without claiming narrative causality.

    We use distinct-date count as a conservative proxy because the ledger stores
    ISO dates and some batches have day-level granularity only.
    """
    by_ref = {row["ref"]: row for row in graph.get("nodes", [])}
    rows = []
    for lifecycle in candidate_lifecycles(graph):
        refs = lifecycle["refs"]
        dates = [by_ref[ref].get("at") for ref in refs if ref in by_ref and by_ref[ref].get("at")]
        unique_dates = sorted(set(dates))
        if len(unique_dates) >= min_days_proxy:
            rows.append({
                "candidate_id": lifecycle["candidate_id"],
                "start": unique_dates[0],
                "end": unique_dates[-1],
                "outcome": lifecycle["outcome"],
                "evidence_refs": refs,
            })
    return rows


def scene_clusters(batches: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Group recurring event kinds and recurring pairs as later scene reservoirs."""
    batches = list(batches)
    kind_refs: defaultdict[str, list[str]] = defaultdict(list)
    kind_dates: defaultdict[str, list[str]] = defaultdict(list)
    pair_refs: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for batch in batches:
        for event in batch.get("events", []):
            ref = event.get("event_id")
            if not ref:
                continue
            kind = str(event.get("event_kind") or "unknown")
            kind_refs[kind].append(ref)
            if event.get("at"):
                kind_dates[kind].append(str(event["at"]))
            speaker, listener = event.get("speaker"), event.get("listener")
            if speaker and listener and listener != "self_record":
                pair_refs[tuple(sorted((str(speaker), str(listener))))].append(ref)
    clusters = []
    for kind, refs in kind_refs.items():
        if len(refs) >= 3:
            clusters.append({
                "cluster_type": "event_kind",
                "label": kind,
                "count": len(refs),
                "date_span": [min(kind_dates[kind]), max(kind_dates[kind])] if kind_dates[kind] else [],
                "evidence_refs": refs,
            })
    for pair, refs in pair_refs.items():
        if len(refs) >= 4:
            clusters.append({
                "cluster_type": "relationship_pair",
                "label": "|".join(pair),
                "count": len(refs),
                "evidence_refs": refs,
            })
    clusters.sort(key=lambda row: (-row["count"], row["label"]))
    return clusters


def viewpoint_coverage(graph: Mapping[str, Any], *, actor_ids: Iterable[str]) -> dict[str, Any]:
    actor_ids = list(actor_ids)
    counts = Counter()
    owned = Counter()
    for node in graph.get("nodes", []):
        for actor in node.get("actors", []):
            if actor in actor_ids:
                counts[actor] += 1
        if node.get("kind") in {"owned_hard_world_event", "actor_state_evidence"}:
            for actor in node.get("actors", []):
                if actor in actor_ids:
                    owned[actor] += 1
    rows = []
    for actor in actor_ids:
        rows.append({
            "actor_id": actor,
            "evidence_count": counts[actor],
            "owned_state_count": owned[actor],
            "coverage": "thin" if counts[actor] < 6 else "moderate" if counts[actor] < 15 else "substantial",
        })
    return {"actors": rows}


def compute_history_thickness_v12(batches: Iterable[Mapping[str, Any]], *, actor_ids: Iterable[str]) -> dict[str, Any]:
    batches = list(batches)
    actor_ids = list(actor_ids)
    graph = build_evidence_graph(batches)
    social_events = [n for n in graph["nodes"] if n["kind"] == "social_event"]
    windows = [w for batch in batches for w in batch.get("windows", [])]
    lifecycles = candidate_lifecycles(graph)
    delayed = delayed_consequence_candidates(graph)
    scenes = scene_clusters(batches)
    coverage = viewpoint_coverage(graph, actor_ids=actor_ids)["actors"]
    years = sorted({str(n.get("at"))[:4] for n in graph["nodes"] if n.get("at")})
    ordinary = sum(1 for n in social_events if n.get("payload", {}).get("act") in ORDINARY_ACTS)
    failed = sum(1 for row in lifecycles if row["outcome"] == "closed_or_failed")
    resolved = sum(1 for row in lifecycles if row["outcome"] != "open_or_ambiguous")
    covered = sum(1 for row in coverage if row["evidence_count"] > 0)
    substantial = sum(1 for row in coverage if row["coverage"] == "substantial")

    components = {
        "actor_coverage": round(18 * covered / max(1, len(actor_ids)), 1),
        "viewpoint_depth": round(12 * substantial / max(1, len(actor_ids)), 1),
        "longitudinal_depth": min(18.0, 3.6 * len(years)),
        "candidate_lifecycle": min(16.0, 1.4 * resolved),
        "delayed_consequences": min(12.0, 1.5 * len(delayed)),
        "recurring_scene_structure": min(10.0, 1.0 * len(scenes)),
        "ordinary_life_density": min(7.0, 7.0 * ordinary / max(1, len(social_events)) / 0.10),
        "failure_and_friction": min(7.0, 1.4 * failed),
    }
    score = round(sum(components.values()), 1)
    gaps = []
    for row in coverage:
        if row["coverage"] == "thin":
            gaps.append(f"thin viewpoint evidence for {row['actor_id']}")
    if ordinary / max(1, len(social_events)) < 0.07:
        gaps.append("ordinary-life density remains low")
    if failed < 4:
        gaps.append("few explicitly failed or closed candidate lifecycles")
    if len(years) < 5:
        gaps.append("longitudinal span is under five years")

    readiness = "thin"
    if score >= 82 and covered == len(actor_ids):
        readiness = "substantial"
    elif score >= 62:
        readiness = "developing"

    return {
        "score": score,
        "readiness": readiness,
        "components": components,
        "window_count": len(windows),
        "social_event_count": len(social_events),
        "evidence_node_count": len(graph["nodes"]),
        "years_present": years,
        "resolved_candidate_lifecycles": resolved,
        "failed_or_closed_lifecycles": failed,
        "delayed_consequence_candidate_count": len(delayed),
        "recurring_scene_cluster_count": len(scenes),
        "viewpoint_coverage": coverage,
        "gaps": gaps,
        "note": "Heuristic readiness for historical/narrative analysis only; never an aesthetic score.",
    }


def build_storyteller_task_v12(*, task_id: str, batches: Iterable[Mapping[str, Any]],
                               actor_ids: Iterable[str], personal_snapshots: Mapping[str, Any] | None = None,
                               as_of: str | None = None) -> dict[str, Any]:
    batches = list(batches)
    actor_ids = list(actor_ids)
    graph = build_evidence_graph(batches)
    thickness = compute_history_thickness_v12(batches, actor_ids=actor_ids)
    timelines = actor_timelines(graph)
    lifecycles = candidate_lifecycles(graph)
    delayed = delayed_consequence_candidates(graph)
    scenes = scene_clusters(batches)
    unresolved = unresolved_threads(graph)
    coverage = viewpoint_coverage(graph, actor_ids=actor_ids)
    refs = [row["ref"] for row in graph["nodes"]]

    return build_task(
        task_id=task_id,
        kind="storyteller_analysis",
        instruction=(
            "Act as a read-only historian, documentary editor and narrative cartographer over an already simulated "
            "world. Do not invent events, motives, dialogue or causality. Use the evidence graph to identify recurring "
            "conflicts, delayed consequences, unresolved threads, scene reservoirs, viewpoint candidates and competing "
            "interpretations. Distinguish mechanically linked candidate lifecycles from interpretive causal chains. "
            "Every interpretation must cite supplied evidence refs. Prefer paths shaped by institutions, money, time, "
            "city, family distance, work routines and relationship history over winner/loser rankings. Literary prose "
            "is disabled: produce an index for later fiction, screenplay or documentary adaptation, not the adaptation itself."
        ),
        payload={
            "as_of": as_of,
            "history_thickness": thickness,
            "actor_timelines": timelines,
            "candidate_lifecycles": lifecycles,
            "delayed_consequence_candidates": delayed,
            "scene_clusters": scenes,
            "unresolved_threads": unresolved,
            "viewpoint_coverage": coverage,
            "personal_snapshots": deepcopy(dict(personal_snapshots or {})),
        },
        output_schema={
            "task_id": task_id,
            "kind": "storyteller_analysis",
            "as_of": as_of,
            "history_thickness_comment": "short evidence-grounded diagnostic",
            "historical_periods": [{"label": "period", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "why_boundary": "...", "evidence_refs": ["ref"]}],
            "recurring_conflicts": [{"label": "conflict", "interpretation": "...", "actors": ["id"], "evidence_refs": ["ref"]}],
            "delayed_consequence_arcs": [{"label": "arc", "steps": ["..."], "actors": ["id"], "evidence_refs": ["ref"]}],
            "unresolved_narrative_threads": [{"label": "thread", "what_is_open": "...", "evidence_refs": ["ref"]}],
            "scene_reservoirs": [{"label": "scene cluster", "dramatic_question": "...", "evidence_refs": ["ref"]}],
            "viewpoint_candidates": [{"actor_id": "id", "why_viewpoint_works": "...", "what_it_hides": "...", "counterargument": "...", "evidence_refs": ["ref"]}],
            "ensemble_structures": [{"label": "ensemble relation", "actors": ["id"], "structure": "...", "evidence_refs": ["ref"]}],
            "underrepresented_lives": [{"actor_id": "id", "gap": "...", "evidence_refs": ["ref if any"]}],
            "competing_interpretations": [{"question": "...", "interpretations": ["..."], "evidence_refs": ["ref"]}],
            "do_not_literarize_yet": ["specific missing evidence or unresolved structural reason"],
            "recommendation": "continue_history|allow_small_literary_probes|ready_for_major_adaptation",
            "evidence_refs": ["union of refs used"],
            "hard_world_writeback": [],
        },
        evidence_refs=refs,
    )


def validate_storyteller_result_v12(task: Mapping[str, Any], result: Mapping[str, Any], *, backend: str) -> dict[str, Any]:
    checked = validate_common_result(task, result, backend=backend)
    allowed = set(task.get("evidence_refs", []))
    evidence_sections = (
        "historical_periods", "recurring_conflicts", "delayed_consequence_arcs",
        "unresolved_narrative_threads", "scene_reservoirs", "viewpoint_candidates",
        "ensemble_structures", "underrepresented_lives", "competing_interpretations",
    )
    used: set[str] = set()
    for section in evidence_sections:
        rows = checked.get(section, [])
        if not isinstance(rows, list):
            raise CognitionProtocolError(f"storyteller section {section} must be a list")
        for row in rows:
            if not isinstance(row, Mapping):
                raise CognitionProtocolError(f"invalid row in {section}")
            refs = set(row.get("evidence_refs", []))
            if section != "underrepresented_lives" and not refs:
                raise CognitionProtocolError(f"storyteller row in {section} lacks evidence refs")
            if not refs.issubset(allowed):
                raise CognitionProtocolError(f"storyteller row in {section} cites unknown evidence")
            used.update(refs)
    if checked.get("hard_world_writeback") not in ([], None):
        raise CognitionProtocolError("Storyteller is read-only")
    if checked.get("recommendation") not in {
        "continue_history", "allow_small_literary_probes", "ready_for_major_adaptation",
    }:
        raise CognitionProtocolError("invalid Storyteller recommendation")
    checked["evidence_refs"] = sorted(used)
    checked["status"] = "read_only_storyteller_v12_analysis_noncanonical"
    return checked
