"""Read-only adaptation planner over the 2026-2035 history.

Storyteller v13 never writes historical facts. It converts evidence-backed
historical clusters into adaptation scene cards that can be ranked, probed and
recombined for novel/screen/animation work.

The module deliberately keeps three layers separate:
1. ledger evidence: immutable historical refs;
2. character/adaptation hypotheses: psychology, shadow, wound, power position;
3. prose probes: disposable fictional renderings that never write back.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Iterable, Mapping


class AdaptationStorytellerError(ValueError):
    pass


HERO_STAGE_FUNCTIONS = {
    "ordinary", "call", "refusal", "threshold", "trial", "descent",
    "insight", "transformation", "return", "post_return_consequence",
}

ARCHETYPE_ROLES = {"mentor", "ally", "shadow", "guardian", "herald", "trickster", "mirror"}

SCENE_TIERS = {"must_keep", "strong", "optional"}

REQUIRED_SCENE_FIELDS = {
    "scene_id", "part", "year", "label", "primary_viewpoint", "participants",
    "evidence_refs", "surface_action", "dramatic_question", "inner_conflict",
    "power_structure", "hero_stage_function", "scene_tier", "scores",
}

SCORE_FIELDS = {
    "historical_leverage",      # changes later choices / resolves prior arc
    "character_revelation",     # exposes a stable trait + shadow
    "relationship_pressure",    # alters or tests relation without requiring rupture
    "material_concreteness",    # money, time, object, place, procedure, body, task
    "power_visibility",         # institutional position actively shapes behavior
    "ordinary_life_counterpoint",# resists all-scenes-are-climaxes structure
    "visual_or_sensory_potential",# can be staged without abstract exposition
}


def _as_set(values: Iterable[str] | None) -> set[str]:
    return {str(x) for x in (values or []) if x}


def allowed_evidence_refs(evidence_graph: Mapping[str, Any]) -> set[str]:
    """Return ledger references that adaptation cards may cite."""
    refs = set()
    for node in evidence_graph.get("nodes", []):
        if node.get("ref"):
            refs.add(str(node["ref"]))
        payload = node.get("payload") or {}
        for key in ("event_id", "candidate_id", "evidence_id"):
            if payload.get(key):
                refs.add(str(payload[key]))
    return refs


def validate_scene_card(
    card: Mapping[str, Any],
    *,
    known_evidence_refs: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Validate one read-only adaptation scene card.

    Psychology/shadow/emotion claims are adaptation hypotheses unless the card
    explicitly marks them evidence-backed. Historical claims must cite ledger
    refs. No card may contain world-writeback instructions.
    """
    missing = REQUIRED_SCENE_FIELDS - set(card)
    if missing:
        raise AdaptationStorytellerError(f"scene card missing fields: {sorted(missing)}")

    checked = deepcopy(dict(card))
    if checked.get("world_writeback") not in (None, False, []):
        raise AdaptationStorytellerError("adaptation scene cards cannot write to historical world")
    checked["world_writeback"] = False

    refs = _as_set(checked.get("evidence_refs"))
    if not refs:
        raise AdaptationStorytellerError("scene card requires historical evidence refs")
    if known_evidence_refs is not None:
        unknown = refs - _as_set(known_evidence_refs)
        if unknown:
            raise AdaptationStorytellerError(f"unknown historical evidence refs: {sorted(unknown)}")

    hero_fn = str(checked.get("hero_stage_function"))
    if hero_fn not in HERO_STAGE_FUNCTIONS:
        raise AdaptationStorytellerError(f"invalid hero_stage_function: {hero_fn}")

    tier = str(checked.get("scene_tier"))
    if tier not in SCENE_TIERS:
        raise AdaptationStorytellerError(f"invalid scene_tier: {tier}")

    roles = checked.get("active_archetype_roles") or []
    for row in roles:
        role = str((row or {}).get("role", ""))
        if role and role not in ARCHETYPE_ROLES:
            raise AdaptationStorytellerError(f"invalid archetype role: {role}")

    scores = checked.get("scores") or {}
    missing_scores = SCORE_FIELDS - set(scores)
    if missing_scores:
        raise AdaptationStorytellerError(f"scene scores missing: {sorted(missing_scores)}")
    for key in SCORE_FIELDS:
        value = scores[key]
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 5:
            raise AdaptationStorytellerError(f"scene score {key} must be 0..5")

    hypotheses = checked.get("adaptation_hypotheses") or {}
    if hypotheses and hypotheses.get("declared_as_history") is True:
        raise AdaptationStorytellerError("adaptation hypotheses cannot declare themselves historical fact")

    return checked


def scene_priority(card: Mapping[str, Any]) -> float:
    """Score scene usefulness without treating score as literary quality."""
    scores = card.get("scores") or {}
    weights = {
        "historical_leverage": 1.45,
        "character_revelation": 1.45,
        "relationship_pressure": 0.85,
        "material_concreteness": 1.05,
        "power_visibility": 1.00,
        "ordinary_life_counterpoint": 0.65,
        "visual_or_sensory_potential": 0.95,
    }
    total = sum(float(scores.get(key, 0)) * weight for key, weight in weights.items())
    tier_boost = {"must_keep": 2.0, "strong": 0.8, "optional": 0.0}.get(card.get("scene_tier"), 0.0)
    return round(total + tier_boost, 3)


def select_balanced_reservoir(
    cards: Iterable[Mapping[str, Any]],
    *,
    limit: int = 26,
    min_per_part: int = 5,
) -> list[dict[str, Any]]:
    """Choose a temporally balanced scene reservoir.

    Selection is structural only. It does not declare selected scenes canonical
    prose, nor does exclusion erase historical importance.
    """
    cards = [validate_scene_card(card) for card in cards]
    by_part: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        by_part[int(card["part"])].append(card)
    for rows in by_part.values():
        rows.sort(key=scene_priority, reverse=True)

    selected: list[dict[str, Any]] = []
    used = set()
    for part in sorted(by_part):
        for card in by_part[part][:min_per_part]:
            selected.append(card)
            used.add(card["scene_id"])

    remaining = [card for card in cards if card["scene_id"] not in used]
    remaining.sort(key=scene_priority, reverse=True)
    for card in remaining:
        if len(selected) >= limit:
            break
        selected.append(card)

    selected.sort(key=lambda row: (int(row["part"]), str(row.get("year")), row["scene_id"]))
    return selected[:limit]


def build_scene_probe_task(
    card: Mapping[str, Any],
    *,
    character_design_refs: Iterable[str],
    style_guardrail_ref: str,
    mode: str = "restrained",
) -> dict[str, Any]:
    """Build a disposable prose-probe task for ChatGPT/DeepSeek/local backend."""
    checked = validate_scene_card(card)
    if mode not in {"restrained", "closer_to_character"}:
        raise AdaptationStorytellerError("probe mode must be restrained or closer_to_character")
    return {
        "task_kind": "adaptation_scene_probe_noncanonical",
        "scene_id": checked["scene_id"],
        "mode": mode,
        "historical_evidence_refs": list(checked["evidence_refs"]),
        "primary_viewpoint": checked["primary_viewpoint"],
        "participants": list(checked["participants"]),
        "dramatic_question": checked["dramatic_question"],
        "surface_action": checked["surface_action"],
        "inner_conflict": checked["inner_conflict"],
        "power_structure": checked["power_structure"],
        "hero_stage_function": checked["hero_stage_function"],
        "active_archetype_roles": deepcopy(checked.get("active_archetype_roles") or []),
        "adaptation_hypotheses": deepcopy(checked.get("adaptation_hypotheses") or {}),
        "character_design_refs": list(character_design_refs),
        "style_guardrail_ref": style_guardrail_ref,
        "instructions": [
            "Do not alter or add hard-world history.",
            "Treat psychology, wounds, secrets and subtext as hypotheses unless supported by evidence.",
            "Let the viewpoint character notice selectively; do not make all participants equally self-aware.",
            "Show one virtue and its shadow in tension without naming the theme.",
            "Let power position affect speech, timing, politeness, permission and consequences.",
            "Do not end with a thesis sentence or life lesson.",
            "Allow unfinished talk, mundane action and emotional ambiguity.",
            "Any invented geography, gestures, domestic detail or minor dialogue is adaptation-only fiction.",
        ],
        "world_writeback": False,
    }


def protagonist_weight_check(cards: Iterable[Mapping[str, Any]], core_actor_ids: Iterable[str]) -> dict[str, Any]:
    """Diagnose viewpoint balance without forcing equal rotation."""
    core = list(core_actor_ids)
    counts = {actor: 0 for actor in core}
    leverage = {actor: 0.0 for actor in core}
    for card in cards:
        actor = str(card.get("primary_viewpoint", ""))
        if actor in counts:
            counts[actor] += 1
            leverage[actor] += scene_priority(card)
    return {
        "viewpoint_scene_counts": counts,
        "viewpoint_priority_mass": {k: round(v, 2) for k, v in leverage.items()},
        "rule": "Unequal weights are allowed. Investigate only if one core actor has zero selected viewpoint scenes or one actor dominates every historical part.",
    }
