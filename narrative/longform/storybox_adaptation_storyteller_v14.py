"""Storyteller v14: nested substories and guest-character micro-arcs.

Read-only adaptation layer. This module may propose adaptation-only characters
for a scene, but it never writes historical ledger facts.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Iterable


class NestedStoryError(ValueError):
    pass


MICRO_ARC_PATTERNS = {
    "position_pressure_choice",
    "ordinary_call_boundary_residue",
    "desire_friction_misjudgment_correction",
    "competence_overreach_cost_recalibration",
    "need_refusal_negotiation_partial_gain",
}

RELATION_FUNCTIONS = {
    "mentor", "ally", "guardian", "shadow", "rival", "mirror",
    "dependent", "client", "authority", "peer", "subordinate", "gatekeeper",
}

POWER_POSITIONS = {"stronger", "weaker", "peer", "cross_cutting"}

GUEST_REQUIRED = {
    "guest_id", "display_name", "current_role", "current_goal", "pressure",
    "virtue", "shadow", "power_position", "information_set",
    "interaction_mode_with_protagonist", "micro_arc_pattern",
    "micro_arc_steps", "status",
}

AUDIT_FIELDS = {
    "time_feasible", "institution_feasible", "professional_feasible",
    "relationship_feasible", "information_feasible", "interest_feasible",
    "psychology_feasible", "era_feasible",
}


def validate_guest_dossier(dossier: Mapping[str, Any]) -> dict[str, Any]:
    missing = GUEST_REQUIRED - set(dossier)
    if missing:
        raise NestedStoryError(f"guest dossier missing fields: {sorted(missing)}")
    row = deepcopy(dict(dossier))
    if row["status"] not in {"adaptation_only_candidate", "adaptation_only_approved"}:
        raise NestedStoryError("guest status must remain adaptation-only")
    if row.get("historical_world_writeback") not in (None, False, []):
        raise NestedStoryError("guest dossier cannot write historical world")
    row["historical_world_writeback"] = False
    if row["power_position"] not in POWER_POSITIONS:
        raise NestedStoryError(f"invalid power_position: {row['power_position']}")
    if row["interaction_mode_with_protagonist"] not in RELATION_FUNCTIONS:
        raise NestedStoryError("invalid interaction function")
    if row["micro_arc_pattern"] not in MICRO_ARC_PATTERNS:
        raise NestedStoryError("invalid micro arc pattern")
    steps = list(row.get("micro_arc_steps") or [])
    if not 3 <= len(steps) <= 5:
        raise NestedStoryError("guest micro arc must have 3-5 steps")
    info = row.get("information_set") or {}
    if "knows" not in info or "does_not_know" not in info:
        raise NestedStoryError("information_set must specify knows and does_not_know")
    return row


def reverse_plausibility_audit(
    dossier: Mapping[str, Any],
    checks: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit an adaptation-only guest before prose use."""
    guest = validate_guest_dossier(dossier)
    missing = AUDIT_FIELDS - set(checks)
    if missing:
        raise NestedStoryError(f"plausibility audit missing: {sorted(missing)}")
    normalized = {key: bool(checks[key]) for key in AUDIT_FIELDS}
    passed = all(normalized.values())
    return {
        "guest_id": guest["guest_id"],
        "checks": normalized,
        "passed": passed,
        "result": "approved_for_disposable_probe" if passed else "revise_or_delete_guest",
        "historical_world_writeback": False,
    }


def validate_substory_card(card: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "substory_id", "protagonist", "time_window", "ordinary_world", "call",
        "threshold_or_resistance", "interaction_chain", "local_transformation",
        "residual_cost", "main_arc_function", "evidence_refs",
    }
    missing = required - set(card)
    if missing:
        raise NestedStoryError(f"substory card missing fields: {sorted(missing)}")
    row = deepcopy(dict(card))
    if not row.get("evidence_refs"):
        raise NestedStoryError("substory must retain evidence refs")
    if row.get("historical_world_writeback") not in (None, False, []):
        raise NestedStoryError("substory adaptation cannot write history")
    row["historical_world_writeback"] = False
    return row


def guest_needed(
    *,
    scene_functions: Iterable[str],
    existing_participant_functions: Mapping[str, Iterable[str]],
) -> dict[str, Any]:
    """Prefer existing relationships; request a guest only for a real function gap."""
    needed = set(scene_functions)
    supplied = set()
    for funcs in existing_participant_functions.values():
        supplied.update(str(x) for x in funcs)
    gap = sorted(needed - supplied)
    return {
        "guest_needed": bool(gap),
        "missing_functions": gap,
        "rule": "Reuse existing characters when natural; create a guest only for unresolved scene functions.",
    }


def build_guest_probe_context(
    *,
    protagonist: str,
    substory: Mapping[str, Any],
    guest: Mapping[str, Any],
    audit: Mapping[str, Any],
    character_context_refs: Iterable[str],
) -> dict[str, Any]:
    """Produce a disposable scene context only after plausibility passes."""
    sub = validate_substory_card(substory)
    gst = validate_guest_dossier(guest)
    if not audit.get("passed"):
        raise NestedStoryError("guest failed reverse plausibility audit")
    return {
        "task_kind": "nested_substory_scene_probe_noncanonical",
        "protagonist": protagonist,
        "substory_id": sub["substory_id"],
        "historical_evidence_refs": list(sub["evidence_refs"]),
        "guest": gst,
        "character_context_refs": list(character_context_refs),
        "instructions": [
            "Treat the guest as a person with a life outside this scene, not a plot device.",
            "Give the guest a legible good, pressure, limited information set and cost.",
            "Do not let the protagonist monopolize moral truth.",
            "Show the guest micro-arc through behavior; never announce Campbell labels.",
            "Any new biography remains adaptation-only fiction.",
            "Do not write back to historical ledger.",
        ],
        "historical_world_writeback": False,
    }
