"""Evaluation helpers for StoryBox Strategic Cognition Kernel v0.

The harness is environment-agnostic.  Live TextArena execution can feed the same
records later, while unit tests and recorded logs can already score belief and
decision quality without an LLM dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .storybox_sck_v0 import BeliefState, SCKError, StrategicDecision


@dataclass(frozen=True)
class VariantConfig:
    variant_id: str
    memory_enabled: bool
    belief_enabled: bool
    planning_depth: int
    communication_separated: bool


DEFAULT_AB_VARIANTS = (
    VariantConfig("plain", False, False, 0, False),
    VariantConfig("memory", True, False, 0, False),
    VariantConfig("belief", True, True, 0, True),
    VariantConfig("belief_planning", True, True, 2, True),
)


@dataclass
class BeliefCheckpoint:
    step_id: str
    belief: BeliefState
    true_hypothesis: str
    informative: bool = True


@dataclass
class ActionCheckpoint:
    step_id: str
    chosen_action_id: str
    action_values: Mapping[str, float]
    chosen_value: float | None = None

    @property
    def best_value(self) -> float:
        if not self.action_values:
            raise SCKError("action checkpoint has no action values")
        return max(float(v) for v in self.action_values.values())

    @property
    def regret(self) -> float:
        if self.chosen_action_id not in self.action_values:
            raise SCKError("chosen action is absent from action value table")
        chosen = (
            float(self.chosen_value)
            if self.chosen_value is not None
            else float(self.action_values[self.chosen_action_id])
        )
        return self.best_value - chosen


@dataclass
class CommunicationCheckpoint:
    step_id: str
    protected_facts: Sequence[str] = ()
    disclosed_facts: Sequence[str] = ()
    contradicted_prior_claim: bool = False
    persuasion_delta: float | None = None

    @property
    def leakage_count(self) -> int:
        protected = set(self.protected_facts)
        return len(protected.intersection(self.disclosed_facts))


@dataclass
class EpisodeEvaluation:
    variant_id: str
    won: bool | None = None
    utility: float | None = None
    belief_checkpoints: list[BeliefCheckpoint] = field(default_factory=list)
    action_checkpoints: list[ActionCheckpoint] = field(default_factory=list)
    communication_checkpoints: list[CommunicationCheckpoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        brier = None
        if self.belief_checkpoints:
            brier = sum(
                row.belief.brier_score(row.true_hypothesis)
                for row in self.belief_checkpoints
            ) / len(self.belief_checkpoints)

        mean_regret = None
        if self.action_checkpoints:
            mean_regret = sum(x.regret for x in self.action_checkpoints) / len(
                self.action_checkpoints
            )

        leakage = sum(x.leakage_count for x in self.communication_checkpoints)
        contradictions = sum(
            1 for x in self.communication_checkpoints if x.contradicted_prior_claim
        )
        persuasion = [
            float(x.persuasion_delta)
            for x in self.communication_checkpoints
            if x.persuasion_delta is not None
        ]

        return {
            "variant_id": self.variant_id,
            "won": self.won,
            "utility": self.utility,
            "mean_brier": brier,
            "mean_action_regret": mean_regret,
            "information_leakage_count": leakage,
            "claim_contradiction_count": contradictions,
            "mean_persuasion_delta": (
                sum(persuasion) / len(persuasion) if persuasion else None
            ),
            "belief_steps": len(self.belief_checkpoints),
            "action_steps": len(self.action_checkpoints),
            "communication_steps": len(self.communication_checkpoints),
            "metadata": dict(self.metadata),
        }


def aggregate_episodes(episodes: Sequence[EpisodeEvaluation]) -> dict[str, dict[str, Any]]:
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for episode in episodes:
        by_variant.setdefault(episode.variant_id, []).append(episode.summary())

    output: dict[str, dict[str, Any]] = {}
    for variant_id, rows in by_variant.items():
        wins = [1.0 if x["won"] else 0.0 for x in rows if x["won"] is not None]
        utilities = [float(x["utility"]) for x in rows if x["utility"] is not None]
        briers = [float(x["mean_brier"]) for x in rows if x["mean_brier"] is not None]
        regrets = [
            float(x["mean_action_regret"])
            for x in rows
            if x["mean_action_regret"] is not None
        ]
        output[variant_id] = {
            "episodes": len(rows),
            "win_rate": sum(wins) / len(wins) if wins else None,
            "mean_utility": sum(utilities) / len(utilities) if utilities else None,
            "mean_brier": sum(briers) / len(briers) if briers else None,
            "mean_action_regret": sum(regrets) / len(regrets) if regrets else None,
            "information_leakage_count": sum(
                int(x["information_leakage_count"]) for x in rows
            ),
            "claim_contradiction_count": sum(
                int(x["claim_contradiction_count"]) for x in rows
            ),
        }
    return output


def decision_to_action_checkpoint(
    step_id: str,
    decision: StrategicDecision,
    oracle_action_values: Mapping[str, float],
) -> ActionCheckpoint:
    """Compare a decision with an offline oracle/value estimator.

    The oracle belongs to evaluation only.  It must never be supplied to SCK at
    decision time, preserving the same truth boundary as StoryBox.
    """
    return ActionCheckpoint(
        step_id=step_id,
        chosen_action_id=decision.action_id,
        action_values=dict(oracle_action_values),
        chosen_value=oracle_action_values.get(decision.action_id),
    )
