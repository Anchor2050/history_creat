"""Strategic Cognition Kernel v0 for StoryBox.

This module is deliberately model-agnostic and dependency-free.  StoryBox owns
truth, visibility, legal actions and world transitions.  SCK receives only an
actor-local information set and chooses a strategic action from that set.

v0 provides:
- auditable probabilistic belief state with evidence-ledger updates;
- lightweight opponent action models;
- generic two-ply expected-value planning over hidden-world hypotheses;
- structured strategic and communication intents;
- calibration helpers for replay/evaluation.

No function in this module accepts or reads StoryBox backstage truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Iterable, Mapping, Sequence


class SCKError(ValueError):
    pass


def _normalize(weights: Mapping[str, float]) -> dict[str, float]:
    clean = {str(k): max(0.0, float(v)) for k, v in weights.items()}
    total = sum(clean.values())
    if total <= 0:
        raise SCKError("probability mass must be positive")
    return {k: v / total for k, v in clean.items()}


def _entropy(probs: Mapping[str, float]) -> float:
    out = 0.0
    for p in probs.values():
        if p > 0:
            out -= p * math.log(p, 2)
    return out


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source: str
    likelihood_ratio_by_hypothesis: Mapping[str, float]
    reliability: float = 1.0
    informative: bool = True
    description: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self, hypotheses: Iterable[str]) -> None:
        if not self.evidence_id:
            raise SCKError("evidence_id is required")
        if not 0.0 <= self.reliability <= 1.0:
            raise SCKError("evidence reliability must be in [0, 1]")
        known = set(hypotheses)
        unknown = set(self.likelihood_ratio_by_hypothesis) - known
        if unknown:
            raise SCKError(f"evidence references unknown hypotheses: {sorted(unknown)}")
        for value in self.likelihood_ratio_by_hypothesis.values():
            if float(value) <= 0:
                raise SCKError("likelihood ratios must be positive")


@dataclass
class BeliefState:
    hypotheses: dict[str, float]
    evidence_ledger: list[dict[str, Any]] = field(default_factory=list)
    last_update: str | None = None

    def __post_init__(self) -> None:
        self.hypotheses = _normalize(self.hypotheses)

    @property
    def entropy(self) -> float:
        return _entropy(self.hypotheses)

    @property
    def confidence(self) -> float:
        if len(self.hypotheses) <= 1:
            return 1.0
        max_entropy = math.log(len(self.hypotheses), 2)
        return 1.0 - self.entropy / max_entropy if max_entropy else 1.0

    def update(self, evidence: EvidenceRecord) -> "BeliefState":
        """Bayesian-style update using auditable likelihood ratios.

        Reliability tempers log-likelihood evidence.  Reliability 0 therefore
        leaves priors untouched; reliability 1 applies the supplied likelihood
        ratios fully.  Non-informative evidence is recorded but does not move the
        posterior.
        """
        evidence.validate(self.hypotheses)
        prior = dict(self.hypotheses)
        posterior_weights: dict[str, float] = {}
        for hypothesis, probability in prior.items():
            lr = float(evidence.likelihood_ratio_by_hypothesis.get(hypothesis, 1.0))
            if not evidence.informative:
                lr = 1.0
            tempered_lr = math.exp(evidence.reliability * math.log(lr))
            posterior_weights[hypothesis] = probability * tempered_lr
        posterior = _normalize(posterior_weights)
        self.hypotheses = posterior
        self.last_update = evidence.evidence_id
        self.evidence_ledger.append(
            {
                "evidence_id": evidence.evidence_id,
                "source": evidence.source,
                "description": evidence.description,
                "reliability": evidence.reliability,
                "informative": evidence.informative,
                "prior": prior,
                "posterior": dict(posterior),
                "entropy_before": _entropy(prior),
                "entropy_after": _entropy(posterior),
                "metadata": dict(evidence.metadata),
            }
        )
        return self

    def probability(self, hypothesis: str) -> float:
        return float(self.hypotheses.get(hypothesis, 0.0))

    def brier_score(self, true_hypothesis: str) -> float:
        if true_hypothesis not in self.hypotheses:
            raise SCKError("true hypothesis is not represented by this belief state")
        return sum(
            (p - (1.0 if h == true_hypothesis else 0.0)) ** 2
            for h, p in self.hypotheses.items()
        ) / len(self.hypotheses)


@dataclass
class OpponentModel:
    actor_id: str
    action_counts: dict[str, float] = field(default_factory=dict)
    prior_strength: float = 1.0
    style_tags: dict[str, float] = field(default_factory=dict)

    def observe_action(self, action_id: str, weight: float = 1.0) -> None:
        if weight < 0:
            raise SCKError("opponent observation weight must be non-negative")
        self.action_counts[action_id] = self.action_counts.get(action_id, 0.0) + weight

    def distribution(self, legal_action_ids: Sequence[str]) -> dict[str, float]:
        if not legal_action_ids:
            return {}
        weights = {
            action_id: self.prior_strength + self.action_counts.get(action_id, 0.0)
            for action_id in legal_action_ids
        }
        return _normalize(weights)


@dataclass(frozen=True)
class StrategicObservation:
    actor_id: str
    game_id: str
    scene_id: str
    round_no: int
    phase: str
    visible_public_state: Mapping[str, Any]
    visible_private_state: Mapping[str, Any]
    legal_actions: Sequence[Mapping[str, Any]]
    reachable_contacts: Sequence[str] = field(default_factory=tuple)
    game_local_role: str | None = None
    game_local_stake: Mapping[str, Any] = field(default_factory=dict)
    game_local_authority: Mapping[str, Any] = field(default_factory=dict)
    commitments: Mapping[str, Any] = field(default_factory=dict)
    reputation: Mapping[str, Any] = field(default_factory=dict)
    fatigue: float = 0.0
    resources: Mapping[str, Any] = field(default_factory=dict)
    cross_game_portfolio_summary: Mapping[str, Any] = field(default_factory=dict)
    observation_history: Sequence[Mapping[str, Any]] = field(default_factory=tuple)

    def action_ids(self) -> list[str]:
        ids = []
        for row in self.legal_actions:
            action_id = str(row.get("action_id", ""))
            if not action_id:
                raise SCKError("every legal action requires action_id")
            ids.append(action_id)
        if len(ids) != len(set(ids)):
            raise SCKError("legal action ids must be unique")
        return ids


@dataclass(frozen=True)
class CommunicationIntent:
    channel: str
    audience: Sequence[str]
    speech_act: str
    disclosure_level: str
    claim_set: Sequence[str] = field(default_factory=tuple)
    omitted_facts: Sequence[str] = field(default_factory=tuple)
    bluff_or_selective_truth: str = "none"
    tone_constraints: Sequence[str] = field(default_factory=tuple)
    floor_bid: float = 0.0


@dataclass(frozen=True)
class StrategicDecision:
    action_id: str
    action: Mapping[str, Any]
    strategic_intent: str
    expected_value: float
    risk_adjusted_value: float
    uncertainty: float
    hypothesis_values: Mapping[str, float]
    protected_information: Sequence[str] = field(default_factory=tuple)
    communication_intent: CommunicationIntent | None = None
    planning_trace: Sequence[Mapping[str, Any]] = field(default_factory=tuple)


# rollout_utility(observation, our_action, hidden_hypothesis,
#                 opponent_actor_id, opponent_action_id) -> utility
RolloutUtility = Callable[
    [StrategicObservation, Mapping[str, Any], str, str | None, str | None],
    float,
]


class StrategicCognitionKernel:
    """Small auditable planner that separates belief, strategy and language."""

    def __init__(self, risk_aversion: float = 0.15):
        if risk_aversion < 0:
            raise SCKError("risk_aversion must be non-negative")
        self.risk_aversion = float(risk_aversion)

    @staticmethod
    def _weighted_mean_and_std(values: Sequence[tuple[float, float]]) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        weight_sum = sum(w for w, _ in values)
        if weight_sum <= 0:
            raise SCKError("rollout weights must sum to positive mass")
        mean = sum(w * v for w, v in values) / weight_sum
        variance = sum(w * (v - mean) ** 2 for w, v in values) / weight_sum
        return mean, math.sqrt(max(0.0, variance))

    def decide(
        self,
        observation: StrategicObservation,
        belief: BeliefState,
        opponent_models: Mapping[str, OpponentModel],
        rollout_utility: RolloutUtility,
        *,
        strategic_intent_by_action: Mapping[str, str] | None = None,
        protected_information: Sequence[str] = (),
    ) -> StrategicDecision:
        """Evaluate every legal action with one opponent-response ply.

        For each hidden-world hypothesis, the kernel averages utility over the
        current action distribution of each modeled opponent.  If no opponent is
        supplied, the evaluator is called once with a null response.  The action
        score is expected utility minus risk_aversion * outcome standard deviation.
        """
        action_ids = observation.action_ids()
        if not action_ids:
            raise SCKError("cannot decide with no legal actions")
        if set(belief.hypotheses) == set():
            raise SCKError("belief state must contain hypotheses")

        traces: list[dict[str, Any]] = []
        scored: list[tuple[float, float, float, Mapping[str, Any], dict[str, float]]] = []
        intents = strategic_intent_by_action or {}

        for action in observation.legal_actions:
            action_id = str(action["action_id"])
            samples: list[tuple[float, float]] = []
            hypothesis_values: dict[str, float] = {}

            for hypothesis, hypothesis_prob in belief.hypotheses.items():
                per_hypothesis_samples: list[tuple[float, float]] = []
                if opponent_models:
                    for opponent_id, model in opponent_models.items():
                        legal_responses = action.get("opponent_legal_actions", {}).get(opponent_id, [])
                        if not legal_responses:
                            utility = float(
                                rollout_utility(observation, action, hypothesis, opponent_id, None)
                            )
                            per_hypothesis_samples.append((1.0, utility))
                            continue
                        response_probs = model.distribution(list(map(str, legal_responses)))
                        for response_id, response_prob in response_probs.items():
                            utility = float(
                                rollout_utility(
                                    observation,
                                    action,
                                    hypothesis,
                                    opponent_id,
                                    response_id,
                                )
                            )
                            per_hypothesis_samples.append((response_prob, utility))
                else:
                    utility = float(rollout_utility(observation, action, hypothesis, None, None))
                    per_hypothesis_samples.append((1.0, utility))

                h_mean, _ = self._weighted_mean_and_std(per_hypothesis_samples)
                hypothesis_values[hypothesis] = h_mean
                for response_weight, utility in per_hypothesis_samples:
                    samples.append((hypothesis_prob * response_weight, utility))

            expected, uncertainty = self._weighted_mean_and_std(samples)
            risk_adjusted = expected - self.risk_aversion * uncertainty
            trace = {
                "action_id": action_id,
                "expected_value": expected,
                "uncertainty": uncertainty,
                "risk_adjusted_value": risk_adjusted,
                "hypothesis_values": dict(hypothesis_values),
            }
            traces.append(trace)
            scored.append((risk_adjusted, expected, uncertainty, action, hypothesis_values))

        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        best_risk, best_expected, best_uncertainty, best_action, best_hypothesis_values = scored[0]
        best_id = str(best_action["action_id"])
        return StrategicDecision(
            action_id=best_id,
            action=dict(best_action),
            strategic_intent=intents.get(best_id, "maximize robust game-local utility under current beliefs"),
            expected_value=best_expected,
            risk_adjusted_value=best_risk,
            uncertainty=best_uncertainty,
            hypothesis_values=dict(best_hypothesis_values),
            protected_information=tuple(protected_information),
            planning_trace=tuple(traces),
        )


def belief_shift(before: BeliefState, after: BeliefState, hypothesis: str) -> float:
    return after.probability(hypothesis) - before.probability(hypothesis)


def mean_brier(states_and_truth: Sequence[tuple[BeliefState, str]]) -> float:
    if not states_and_truth:
        raise SCKError("cannot score an empty belief replay")
    return sum(state.brier_score(truth) for state, truth in states_and_truth) / len(states_and_truth)
