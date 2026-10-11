"""Game-design and moderator quality gate for StoryBox.

This module audits a Game design before play. It does not generate prose and it
never changes fixed truth. The aim is to distinguish a merely legal game from a
high-skill, replayable narrative game with inference, counterplay and bounded
moderator discretion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class GameDesignError(ValueError):
    pass


KNOWN_MECHANICS = {
    "hidden_interest",
    "asymmetric_information",
    "public_evidence_trail",
    "private_channel",
    "proposal_vote_mission",
    "moderator_information",
    "investigation_clue_economy",
    "attention_budget",
    "resource_conversion",
    "map_unlock",
    "phase_clock",
    "simultaneous_action",
    "bluff_costly_signal",
    "role_ability",
    "campaign_persistence",
    "multi_game_portfolio",
    "event_node_gate",
}


@dataclass
class GameDesignSpec:
    game_id: str
    objective: str
    primary_mechanics: list[str]
    truth_fixed_before_play: bool = True
    public_evidence_rate: float = 0.5
    private_information_density: float = 0.5
    moderator_discretion: float = 0.3
    strategic_branching: int = 2
    counterplay_paths: int = 2
    evidence_redundancy: int = 2
    dominant_actor_share: float = 0.35
    stochasticity: float = 0.15
    action_budget_pressure: float = 0.5
    deadline_pressure: float = 0.5
    false_belief_possible: bool = True
    game_can_deadlock: bool = True
    game_can_fail: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass
class DesignAudit:
    passed: bool
    hard_failures: list[str]
    warnings: list[str]
    strengths: list[str]
    scores: dict[str, float]


def _unit(x: float, name: str) -> float:
    value = float(x)
    if value < 0.0 or value > 1.0:
        raise GameDesignError(f"{name} must be between 0 and 1")
    return value


def validate_spec(spec: GameDesignSpec) -> None:
    if not spec.game_id or not spec.objective:
        raise GameDesignError("game_id and objective are required")
    if not spec.primary_mechanics:
        raise GameDesignError("at least one primary mechanic is required")
    unknown = [m for m in spec.primary_mechanics if m not in KNOWN_MECHANICS]
    if unknown:
        raise GameDesignError(f"unknown mechanics: {unknown}")
    if len(spec.primary_mechanics) > 7:
        raise GameDesignError("too many primary mechanics; split the game")
    for name in (
        "public_evidence_rate",
        "private_information_density",
        "moderator_discretion",
        "dominant_actor_share",
        "stochasticity",
        "action_budget_pressure",
        "deadline_pressure",
    ):
        _unit(getattr(spec, name), name)
    if spec.strategic_branching < 1:
        raise GameDesignError("strategic_branching must be >= 1")
    if spec.counterplay_paths < 0:
        raise GameDesignError("counterplay_paths must be >= 0")
    if spec.evidence_redundancy < 0:
        raise GameDesignError("evidence_redundancy must be >= 0")


def _inferential_leverage(spec: GameDesignSpec) -> float:
    evidence = spec.public_evidence_rate
    redundancy = min(1.0, spec.evidence_redundancy / 3.0)
    noise_penalty = 0.45 * spec.stochasticity
    private_balance = 1.0 - abs(spec.private_information_density - 0.55)
    return max(0.0, min(1.0, 0.45 * evidence + 0.3 * redundancy + 0.25 * private_balance - noise_penalty))


def _strategy_quality(spec: GameDesignSpec) -> float:
    branching = min(1.0, spec.strategic_branching / 4.0)
    counterplay = min(1.0, spec.counterplay_paths / 3.0)
    return 0.55 * branching + 0.45 * counterplay


def _moderator_fairness(spec: GameDesignSpec) -> float:
    fixed_bonus = 0.25 if spec.truth_fixed_before_play else 0.0
    discretion_penalty = 0.65 * spec.moderator_discretion
    return max(0.0, min(1.0, 0.75 + fixed_bonus - discretion_penalty))


def _power_distribution(spec: GameDesignSpec) -> float:
    # 0.33 is a healthy default for one influential actor in a multi-actor game.
    if spec.dominant_actor_share <= 0.4:
        return 1.0
    return max(0.0, 1.0 - (spec.dominant_actor_share - 0.4) * 2.2)


def _pressure_quality(spec: GameDesignSpec) -> float:
    # Zero pressure produces drift; extreme pressure removes strategy.
    target = 0.58
    combined = 0.5 * spec.action_budget_pressure + 0.5 * spec.deadline_pressure
    return max(0.0, 1.0 - abs(combined - target) * 1.7)


def audit_game_design(spec: GameDesignSpec) -> DesignAudit:
    validate_spec(spec)
    hard: list[str] = []
    warnings: list[str] = []
    strengths: list[str] = []

    scores = {
        "inferential_leverage": _inferential_leverage(spec),
        "strategy_quality": _strategy_quality(spec),
        "moderator_fairness": _moderator_fairness(spec),
        "power_distribution": _power_distribution(spec),
        "pressure_quality": _pressure_quality(spec),
    }

    if not spec.truth_fixed_before_play and any(
        m in spec.primary_mechanics
        for m in {"asymmetric_information", "hidden_interest", "investigation_clue_economy"}
    ):
        hard.append("mystery/information game requires fixed backstage truth before play")

    if spec.strategic_branching < 2:
        hard.append("only one meaningful strategy branch; puzzle is effectively scripted")

    if spec.counterplay_paths < 1:
        hard.append("no counterplay path against a plausible dominant strategy")

    if spec.moderator_discretion > 0.7:
        hard.append("moderator discretion is high enough to overwrite player skill")

    if spec.public_evidence_rate < 0.15 and spec.private_information_density > 0.75:
        hard.append("too little public trace for players to update beliefs from others' actions")

    if spec.dominant_actor_share > 0.72:
        hard.append("one actor controls too much of the critical action space")

    if spec.stochasticity > 0.65 and "public_evidence_trail" not in spec.primary_mechanics:
        hard.append("high randomness without durable evidence makes inference mostly luck")

    if not spec.game_can_fail:
        warnings.append("game cannot fail; decisions may lack consequence")
    if not spec.game_can_deadlock:
        warnings.append("game cannot deadlock; engine may be forced to invent progress")
    if spec.evidence_redundancy == 0 and "investigation_clue_economy" in spec.primary_mechanics:
        warnings.append("single-source clues create brittle mystery design")
    if spec.private_information_density < 0.1 and "asymmetric_information" in spec.primary_mechanics:
        warnings.append("asymmetric-information mechanic is configured with almost no asymmetry")
    if spec.action_budget_pressure > 0.9:
        warnings.append("action pressure may be so high that players cannot explore alternatives")
    if spec.deadline_pressure < 0.1 and "phase_clock" in spec.primary_mechanics:
        warnings.append("clock exists but exerts almost no strategic pressure")

    if scores["inferential_leverage"] >= 0.65:
        strengths.append("skilled players can plausibly outperform by reasoning from evidence")
    if scores["strategy_quality"] >= 0.65:
        strengths.append("multiple viable lines and counterplay are available")
    if scores["moderator_fairness"] >= 0.7:
        strengths.append("moderator has useful discretion without owning the result")
    if scores["power_distribution"] >= 0.75:
        strengths.append("no single actor trivially solves or blocks the whole game")
    if scores["pressure_quality"] >= 0.7:
        strengths.append("time/resource pressure is meaningful without eliminating choice")

    weighted = (
        0.27 * scores["inferential_leverage"]
        + 0.25 * scores["strategy_quality"]
        + 0.2 * scores["moderator_fairness"]
        + 0.15 * scores["power_distribution"]
        + 0.13 * scores["pressure_quality"]
    )
    scores["overall"] = weighted

    if weighted < 0.52:
        hard.append("overall game-design quality below minimum threshold")

    return DesignAudit(
        passed=not hard,
        hard_failures=hard,
        warnings=warnings,
        strengths=strengths,
        scores=scores,
    )


def mechanic_overlap_penalty(game_specs: list[GameDesignSpec]) -> dict[str, Any]:
    """Detect an event arc where every Game uses the same trick.

    Variety is not an end in itself, but repeated identical mechanism bundles make
    an event arc feel like the same game reskinned.
    """
    if not game_specs:
        return {"penalty": 0.0, "pairs": []}
    pairs = []
    total = 0.0
    count = 0
    for i, left in enumerate(game_specs):
        a = set(left.primary_mechanics)
        for right in game_specs[i + 1 :]:
            b = set(right.primary_mechanics)
            union = a | b
            overlap = len(a & b) / max(1, len(union))
            pairs.append({"a": left.game_id, "b": right.game_id, "jaccard": overlap})
            total += overlap
            count += 1
    avg = total / max(1, count)
    return {
        "penalty": max(0.0, (avg - 0.58) / 0.42),
        "average_overlap": avg,
        "pairs": pairs,
    }
