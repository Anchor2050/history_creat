"""Evidence-grounded Personal layer for the fourteen-person world.

Personal state is not a hidden-author oracle. It is a candidate interpretation
of one actor's own remembered experience. Every inferred concern, goal or
interpretation must cite supplied evidence. Personal results may shape later
attention and behavior tasks, but cannot directly create jobs, money, social
ties, projects, publications or other hard-world facts.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .storybox_cognition_protocol_v11 import build_task, validate_common_result, CognitionProtocolError


PERSONAL_FIELDS = (
    "current_concerns",
    "private_goals",
    "unresolved_tensions",
    "routine_preferences",
    "interpretations",
    "attention_priorities",
)


def _event_ref(event: Mapping[str, Any]) -> str | None:
    return event.get("event_id") or event.get("candidate_id")


def collect_actor_evidence(actor_id: str, batches: Iterable[Mapping[str, Any]], *, limit: int = 80) -> list[dict[str, Any]]:
    """Collect only evidence the actor directly participated in or owns."""
    rows: list[dict[str, Any]] = []
    for batch in batches:
        for event in batch.get("events", []):
            if actor_id not in (event.get("speaker"), event.get("listener")):
                continue
            ref = _event_ref(event)
            if not ref:
                continue
            rows.append({
                "ref": ref,
                "at": event.get("at"),
                "kind": "social_event",
                "role": "speaker" if event.get("speaker") == actor_id else "listener",
                "act": event.get("act"),
                "content": event.get("content"),
            })
        for row in batch.get("actor_state_evidence", []):
            if row.get("actor") != actor_id:
                continue
            ref = row.get("evidence_id") or f"state:{batch.get('batch_id')}:{row.get('at')}:{row.get('dimension')}"
            rows.append({
                "ref": ref,
                "at": row.get("at"),
                "kind": "actor_state_evidence",
                "dimension": row.get("dimension"),
                "content": row.get("evidence"),
            })
        for event in batch.get("exogenous_hard_world_events", []):
            if event.get("actor") != actor_id:
                continue
            ref = _event_ref(event)
            if not ref:
                continue
            rows.append({
                "ref": ref,
                "at": event.get("at"),
                "kind": "owned_hard_world_event",
                "content": {k: v for k, v in event.items() if k not in {"visibility"}},
            })
    rows.sort(key=lambda row: (row.get("at") or "", row.get("ref") or ""))
    return rows[-limit:]


def build_personal_task(actor_id: str, evidence: list[Mapping[str, Any]], *,
                        prior_state: Mapping[str, Any] | None = None,
                        as_of: str | None = None) -> dict[str, Any]:
    refs = [row["ref"] for row in evidence if row.get("ref")]
    return build_task(
        task_id=f"personal:{actor_id}:{as_of or 'current'}",
        kind="personal_reflection",
        instruction=(
            "Infer a conservative Personal-state candidate for this actor using only supplied evidence. "
            "Write from the actor's plausible internal point of view without inventing memories, diagnoses, "
            "secret facts, resources or outcomes. Distinguish recurring concern from temporary reaction. "
            "Every non-empty item must cite one or more allowed evidence refs. It is valid to leave a field empty. "
            "This layer cannot change hard-world state by itself."
        ),
        payload={
            "actor_id": actor_id,
            "as_of": as_of,
            "prior_personal_state": deepcopy(dict(prior_state or {})),
            "evidence": deepcopy(evidence),
        },
        output_schema={
            "task_id": "same task id",
            "kind": "personal_reflection",
            "actor_id": actor_id,
            "fields": {
                name: [{"text": "short candidate statement", "evidence_refs": ["ref"], "confidence": "low|medium|high"}]
                for name in PERSONAL_FIELDS
            },
            "continuity": [{"text": "what persisted or changed", "evidence_refs": ["ref"]}],
            "unknowns": ["questions the evidence does not support answering"],
            "evidence_refs": ["union of refs actually used"],
            "hard_world_writeback": [],
        },
        evidence_refs=refs,
    )


def validate_personal_result(task: Mapping[str, Any], result: Mapping[str, Any], *, backend: str) -> dict[str, Any]:
    checked = validate_common_result(task, result, backend=backend)
    if checked.get("actor_id") != task.get("payload", {}).get("actor_id"):
        raise CognitionProtocolError("personal result actor_id mismatch")
    fields = checked.get("fields")
    if not isinstance(fields, Mapping):
        raise CognitionProtocolError("personal result requires fields mapping")
    allowed = set(task.get("evidence_refs", []))
    used: set[str] = set()
    for field_name in PERSONAL_FIELDS:
        items = fields.get(field_name, [])
        if not isinstance(items, list):
            raise CognitionProtocolError(f"personal field {field_name} must be a list")
        for item in items:
            if not isinstance(item, Mapping) or not isinstance(item.get("text"), str):
                raise CognitionProtocolError(f"invalid personal item in {field_name}")
            refs = set(item.get("evidence_refs", []))
            if not refs or not refs.issubset(allowed):
                raise CognitionProtocolError(f"personal item in {field_name} lacks valid evidence refs")
            if item.get("confidence") not in {"low", "medium", "high"}:
                raise CognitionProtocolError("personal confidence must be low/medium/high")
            used.update(refs)
    for item in checked.get("continuity", []):
        refs = set(item.get("evidence_refs", [])) if isinstance(item, Mapping) else set()
        if not refs or not refs.issubset(allowed):
            raise CognitionProtocolError("continuity item lacks valid evidence refs")
        used.update(refs)
    if checked.get("hard_world_writeback") not in ([], None):
        raise CognitionProtocolError("Personal layer may not directly write hard-world facts")
    checked["evidence_refs"] = sorted(used)
    checked["status"] = "inferred_personal_candidate_noncanonical"
    return checked
