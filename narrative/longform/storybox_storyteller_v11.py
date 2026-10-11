"""Read-only Storyteller for the chatbot-led long history.

At this stage Storyteller is a historian/editor, not an author with world-write
permission. It can compress evidence, identify recurring conflicts, candidate
viewpoints and scene clusters, and diagnose whether the history is thick
enough for later literary work. Every narrative claim must be traceable to
ledger evidence. Literary prose generation is deliberately deferred.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any, Iterable, Mapping

from .storybox_cognition_protocol_v11 import build_task, validate_common_result, CognitionProtocolError


FAILURE_TOKENS = (
    "reject", "rejected", "closed", "no_offer", "below_cutoff", "refuted",
    "failed", "not_selected", "false", "declined",
)
ORDINARY_ACTS = {"small_talk", "check_in"}


def _all_events(batches: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for batch in batches:
        rows.extend(deepcopy(batch.get("events", [])))
    return rows


def compute_history_thickness(batches: Iterable[Mapping[str, Any]], *, actor_ids: Iterable[str]) -> dict[str, Any]:
    """Heuristic diagnostics, not an aesthetic score.

    The score is intentionally decomposed so later literary decisions can see
    what is missing instead of treating one number as truth.
    """
    batches = list(batches)
    actor_ids = list(actor_ids)
    events = _all_events(batches)
    windows = [window for batch in batches for window in batch.get("windows", [])]
    updates = [row for batch in batches for row in batch.get("hard_world_candidate_updates", [])]

    coverage = Counter()
    pair_counts = Counter()
    ordinary = 0
    for event in events:
        speaker, listener = event.get("speaker"), event.get("listener")
        if speaker in actor_ids:
            coverage[speaker] += 1
        if listener in actor_ids:
            coverage[listener] += 1
        if speaker and listener:
            pair_counts[tuple(sorted((speaker, listener)))] += 1
        if event.get("act") in ORDINARY_ACTS:
            ordinary += 1

    failure_updates = 0
    resolved_updates = 0
    for row in updates:
        result = str(row.get("result", "")).lower()
        if result:
            resolved_updates += 1
        if any(token in result for token in FAILURE_TOKENS):
            failure_updates += 1

    dates = [str(event.get("at")) for event in events if event.get("at")]
    years = sorted({date[:4] for date in dates if len(date) >= 4})
    repeated_pairs = sum(1 for count in pair_counts.values() if count >= 2)
    covered_actors = sum(1 for actor in actor_ids if coverage[actor] > 0)

    components = {
        "actor_coverage": round(25 * covered_actors / max(1, len(actor_ids)), 1),
        "longitudinal_depth": min(20.0, 5.0 * len(years)),
        "candidate_lifecycle": min(20.0, 2.0 * resolved_updates),
        "relationship_continuity": min(15.0, 1.5 * repeated_pairs),
        "ordinary_life_density": min(10.0, 10.0 * ordinary / max(1, len(events)) / 0.12),
        "failure_and_friction": min(10.0, 2.0 * failure_updates),
    }
    score = round(sum(components.values()), 1)

    missing = []
    for actor in actor_ids:
        if coverage[actor] == 0:
            missing.append(f"no explicit event evidence for {actor}")
        elif coverage[actor] < 3:
            missing.append(f"thin explicit event evidence for {actor}")
    if ordinary / max(1, len(events)) < 0.08:
        missing.append("ordinary-life interactions are sparse relative to consequential events")
    if failure_updates < 3:
        missing.append("too few failed/closed/refuted candidate lifecycles")
    if len(years) < 3:
        missing.append("longitudinal span is still short")

    readiness = "thin"
    if score >= 80 and not any(item.startswith("no explicit") for item in missing):
        readiness = "substantial"
    elif score >= 60:
        readiness = "developing"

    return {
        "score": score,
        "readiness": readiness,
        "components": components,
        "window_count": len(windows),
        "event_count": len(events),
        "covered_actor_count": covered_actors,
        "actor_count": len(actor_ids),
        "years_present": years,
        "resolved_candidate_updates": resolved_updates,
        "failed_or_closed_updates": failure_updates,
        "repeated_relationship_pairs": repeated_pairs,
        "ordinary_event_count": ordinary,
        "gaps": missing,
        "note": "Heuristic history-thickness diagnostic only; not a measure of literary quality.",
    }


def build_storyteller_task(*, task_id: str, batches: Iterable[Mapping[str, Any]], actor_ids: Iterable[str],
                           personal_snapshots: Mapping[str, Any] | None = None,
                           mode: str = "diagnostic") -> dict[str, Any]:
    batches = list(batches)
    events = _all_events(batches)
    evidence_rows = []
    for event in events:
        if not event.get("event_id"):
            continue
        evidence_rows.append({
            "ref": event["event_id"],
            "at": event.get("at"),
            "event_kind": event.get("event_kind"),
            "speaker": event.get("speaker"),
            "listener": event.get("listener"),
            "act": event.get("act"),
            "content": event.get("content"),
        })
    thickness = compute_history_thickness(batches, actor_ids=actor_ids)
    refs = [row["ref"] for row in evidence_rows]
    return build_task(
        task_id=task_id,
        kind="storyteller_analysis",
        instruction=(
            "Act as a read-only historian/editor over an already simulated world. Do not invent events, dialogue, "
            "motives or causal links. Identify only narrative structures supported by supplied evidence. Separate "
            "fact from interpretation. Every proposed conflict, arc, protagonist candidate or scene cluster must "
            "cite event refs. Do not write novel prose in diagnostic mode and do not propose any hard-world writeback. "
            "Prefer recurring tensions and delayed consequences over a winner/loser ranking. Point out missing evidence "
            "and competing interpretations."
        ),
        payload={
            "mode": mode,
            "history_thickness": thickness,
            "events": evidence_rows,
            "personal_snapshots": deepcopy(dict(personal_snapshots or {})),
        },
        output_schema={
            "task_id": task_id,
            "kind": "storyteller_analysis",
            "history_thickness_comment": "short interpretation of deterministic diagnostic",
            "recurring_conflicts": [{"label": "conflict", "interpretation": "...", "evidence_refs": ["event"]}],
            "causal_chains": [{"label": "chain", "steps": ["..."], "evidence_refs": ["event"]}],
            "protagonist_candidates": [{"actor_id": "...", "why": "...", "counterargument": "...", "evidence_refs": ["event"]}],
            "scene_clusters": [{"label": "possible later scene", "why": "...", "evidence_refs": ["event"]}],
            "underrepresented_lives": [{"actor_id": "...", "gap": "...", "evidence_refs": ["event if any"]}],
            "competing_interpretations": [{"question": "...", "interpretations": ["..."], "evidence_refs": ["event"]}],
            "recommendation": "continue_history|ready_for_literary_experiment",
            "evidence_refs": ["union of refs used"],
            "hard_world_writeback": [],
        },
        evidence_refs=refs,
    )


def validate_storyteller_result(task: Mapping[str, Any], result: Mapping[str, Any], *, backend: str) -> dict[str, Any]:
    checked = validate_common_result(task, result, backend=backend)
    allowed = set(task.get("evidence_refs", []))
    sections = (
        "recurring_conflicts", "causal_chains", "protagonist_candidates",
        "scene_clusters", "underrepresented_lives", "competing_interpretations",
    )
    used: set[str] = set()
    for section in sections:
        rows = checked.get(section, [])
        if not isinstance(rows, list):
            raise CognitionProtocolError(f"storyteller section {section} must be a list")
        for row in rows:
            if not isinstance(row, Mapping):
                raise CognitionProtocolError(f"invalid storyteller row in {section}")
            refs = set(row.get("evidence_refs", []))
            # A gap may legitimately have no direct event because absence is the point.
            if section != "underrepresented_lives" and not refs:
                raise CognitionProtocolError(f"storyteller row in {section} lacks evidence refs")
            if not refs.issubset(allowed):
                raise CognitionProtocolError(f"storyteller row in {section} cites unknown evidence")
            used.update(refs)
    if checked.get("hard_world_writeback") not in ([], None):
        raise CognitionProtocolError("Storyteller is read-only and may not change world history")
    if checked.get("recommendation") not in {"continue_history", "ready_for_literary_experiment"}:
        raise CognitionProtocolError("invalid storyteller recommendation")
    checked["evidence_refs"] = sorted(used)
    checked["status"] = "read_only_storyteller_analysis_noncanonical"
    return checked
