"""Normal/abnormal behavior routing without random plot forcing.

StoryBox's original branch toggles abnormal behavior from a random factor and
uses special prompts. This branch keeps the useful idea of a behavior-mode
split but makes an abnormal action an auditable deviation from that actor's
own baseline. 'Abnormal' here means out-of-pattern, not mental illness.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .storybox_cognition_protocol_v11 import build_task, validate_common_result, CognitionProtocolError


BEHAVIOR_MODES = {"normal", "abnormal"}
TRIGGER_TYPES = {
    "pressure_accumulation",
    "acute_shock",
    "value_conflict",
    "relationship_rupture",
    "rare_opportunity",
    "exhaustion",
    "deliberate_experiment",
}


def build_behavior_task(*, task_id: str, actor_id: str, visible_state: Mapping[str, Any],
                        retrieved_memories: list[Mapping[str, Any]],
                        personal_state: Mapping[str, Any] | None,
                        feasible_actions: list[Mapping[str, Any]],
                        evidence_refs: list[str],
                        abnormal_used_in_period: int = 0,
                        abnormal_budget: int = 1) -> dict[str, Any]:
    return build_task(
        task_id=task_id,
        kind="behavior_decision",
        instruction=(
            "Choose a feasible action for the actor. First infer the actor's expected baseline action from "
            "visible state, retrieved memories and evidence-grounded Personal state. Use mode=normal unless a "
            "specific supplied trigger makes an out-of-pattern choice plausible. An abnormal action must name "
            "what baseline it deviates from, why now, and the evidence refs supporting the trigger. Abnormal does "
            "not mean bizarre, irrational or malicious. It cannot grant new knowledge, money, authority, access, "
            "relationships or physical ability. It may still be quiet: e.g. refusing work they usually accept, "
            "calling someone they normally avoid, leaving early, applying somewhere unexpected, or speaking more "
            "directly than usual. If no earned deviation exists, choose normal."
        ),
        payload={
            "actor_id": actor_id,
            "visible_state": deepcopy(dict(visible_state)),
            "retrieved_memories": deepcopy(retrieved_memories),
            "personal_state": deepcopy(dict(personal_state or {})),
            "feasible_actions": deepcopy(feasible_actions),
            "abnormal_used_in_period": abnormal_used_in_period,
            "abnormal_budget": abnormal_budget,
        },
        output_schema={
            "task_id": task_id,
            "kind": "behavior_decision",
            "actor_id": actor_id,
            "mode": "normal|abnormal",
            "chosen_action_id": "one feasible action id",
            "baseline_expected_action": "short description",
            "deviation": "empty for normal; what differs for abnormal",
            "trigger_type": "null for normal; one allowed trigger type for abnormal",
            "trigger_refs": ["required for abnormal"],
            "reason": "short causal explanation",
            "constraint_check": {"feasible": True, "notes": "why constraints still hold"},
            "evidence_refs": ["refs actually used"],
        },
        evidence_refs=evidence_refs,
    )


def validate_behavior_result(task: Mapping[str, Any], result: Mapping[str, Any], *, backend: str) -> dict[str, Any]:
    checked = validate_common_result(task, result, backend=backend)
    payload = task.get("payload", {})
    if checked.get("actor_id") != payload.get("actor_id"):
        raise CognitionProtocolError("behavior actor_id mismatch")
    mode = checked.get("mode")
    if mode not in BEHAVIOR_MODES:
        raise CognitionProtocolError("behavior mode must be normal or abnormal")
    action_ids = {row.get("action_id") for row in payload.get("feasible_actions", [])}
    if checked.get("chosen_action_id") not in action_ids:
        raise CognitionProtocolError("chosen action was not supplied as feasible")
    constraint = checked.get("constraint_check", {})
    if not isinstance(constraint, Mapping) or constraint.get("feasible") is not True:
        raise CognitionProtocolError("behavior result must preserve hard constraints")

    if mode == "normal":
        if checked.get("trigger_refs") not in ([], None) or checked.get("trigger_type") not in (None, ""):
            raise CognitionProtocolError("normal behavior must not fabricate abnormal trigger")
    else:
        if payload.get("abnormal_used_in_period", 0) >= payload.get("abnormal_budget", 1):
            raise CognitionProtocolError("abnormal behavior budget exhausted")
        if checked.get("trigger_type") not in TRIGGER_TYPES:
            raise CognitionProtocolError("abnormal behavior needs an allowed trigger type")
        refs = set(checked.get("trigger_refs", []))
        allowed = set(task.get("evidence_refs", []))
        if not refs or not refs.issubset(allowed):
            raise CognitionProtocolError("abnormal behavior requires supplied trigger evidence")
        if not checked.get("baseline_expected_action") or not checked.get("deviation"):
            raise CognitionProtocolError("abnormal behavior must state baseline and deviation")

    checked["status"] = "behavior_decision_candidate_noncanonical"
    checked["world_writeback"] = "none_until_event_execution_and_feasibility_commit"
    return checked
