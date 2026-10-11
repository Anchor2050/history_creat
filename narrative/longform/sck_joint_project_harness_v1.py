"""SCK harness for the mixed-motive Joint Project substrate.

Contract: ``docs/adaptation/sck-mixed-motive-benchmark-contract-v1.md``.
Substrate: :mod:`narrative.longform.sck_joint_project_env_v1`.

Delivers the peer-mandated ablation over ``plain``, ``memory``, ``belief`` and
``belief_planning`` plus fixed, non-learning alternative policies, and a 20-50
episode smoke A/B with mechanism diagnostics.

Information boundary
--------------------
* Policies receive only :class:`~narrative.longform.sck_joint_project_env_v1.AgentView`
  objects.  They never receive the environment, and the environment's
  ``true_types`` is read only in evaluation and in the calibration label.
* :func:`evaluate_episode` is the only place truth is consumed.
* Recording the type posterior for calibration snapshots it, because the live
  posterior keeps updating.

Explicit modelling choices (kept separate and auditable)
-------------------------------------------------------
* **Behavioural rule used for prediction, not for evidence.**  The belief layer
  predicts that another agent contributes ``max_contribution`` when its cost type
  is at most 2, else 0.  That rule follows from the payoff: three units cost
  ``3*c`` and the bonus is 6, so a type-1 agent gains 3 and a type-2 agent breaks
  even, while a type-4 agent loses 6.  It is a documented simplification of
  rational play, not a claim about it.
* **Evidence is only the aggregate surplus.**  The likelihood of a hypothesis is
  1 exactly when it reproduces the observed aggregate surplus, and 0 otherwise.
  No behavioural assumption enters the evidence, so belief calibration is not
  circular with the prediction rule.
* ``belief_planning`` adds a one-ply response model conditioned on the round's
  public pledges and each agent's measured pledge-keeping reliability.  It is
  pledge-conditioned opponent adaptation, not search, and is labelled as such.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from itertools import combinations, product
import json
from pathlib import Path
import random
import time
from typing import Any, Mapping, Sequence

from .sck_joint_project_env_v1 import (
    PHASE_CONTRIBUTE,
    PHASE_PLEDGE,
    AgentView,
    JointProjectConfig,
    JointProjectEnv,
    RoundRecord,
    best_own_contribution_given_realised_others,
    full_information_optimum,
    round_joint_surplus,
)

#: Cost types at or below this threshold are predicted to contribute the maximum.
PREDICTED_CONTRIBUTOR_COST_CEILING = 2
#: Beta-style pseudo-counts for an agent's pledge reliability.  The mean of the
#: prior is ``PLEDGE_RELIABILITY_ALPHA / (ALPHA + BETA)``.
PLEDGE_RELIABILITY_ALPHA = 0.6
PLEDGE_RELIABILITY_BETA = 0.4
PLEDGE_RELIABILITY_PRIOR = PLEDGE_RELIABILITY_ALPHA / (
    PLEDGE_RELIABILITY_ALPHA + PLEDGE_RELIABILITY_BETA
)


def _type_hypotheses(config: JointProjectConfig) -> tuple[tuple[int, ...], ...]:
    return tuple(product(config.type_values, repeat=config.num_agents))


def _hypothesis_prior(
    hypothesis: Sequence[int], config: JointProjectConfig
) -> float:
    weight = 1.0
    for cost in hypothesis:
        weight *= config.type_probabilities[config.type_values.index(int(cost))]
    return weight


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


class JointProjectPolicy:
    """Base policy: uniform random legal value, no memory and no belief."""

    variant_id = "plain"

    def __init__(
        self, *, agent_id: int, config: JointProjectConfig, seed: int
    ) -> None:
        self.agent_id = agent_id
        self.config = config
        # Own RNG so a policy can never perturb environment randomness.
        self.rng = random.Random(seed)
        self.uses_memory = False
        self.uses_belief = False

    # -- helpers ---------------------------------------------------------
    def _others(self, view: AgentView) -> tuple[int, ...]:
        return view.other_agents

    def _total_contributions(self, view: AgentView) -> int:
        if not view.pledges_this_round:
            return 0
        return sum(value for _agent, value in view.pledges_this_round)

    # -- protocol --------------------------------------------------------
    def choose_pledge(self, view: AgentView) -> int:
        return self.rng.choice(view.legal_values)

    def choose_contribution(self, view: AgentView) -> int:
        return self.rng.choice(view.legal_values)

    def act(self, view: AgentView) -> int:
        if view.phase == PHASE_PLEDGE:
            return self.choose_pledge(view)
        if view.phase == PHASE_CONTRIBUTE:
            return self.choose_contribution(view)
        raise ValueError(f"unknown phase: {view.phase}")


class FixedCostThresholdPolicy(JointProjectPolicy):
    """Fixed, non-learning policy: contribute the maximum iff cheap, else 0.

    This is the contract's documented reference behaviour and doubles as the
    fixed alternative opponent required by the peer decision.
    """

    variant_id = "fixed_cost_threshold"

    def choose_pledge(self, view: AgentView) -> int:
        return self._plan(view)

    def choose_contribution(self, view: AgentView) -> int:
        return self._plan(view)

    def _plan(self, view: AgentView) -> int:
        if view.own_type <= PREDICTED_CONTRIBUTOR_COST_CEILING:
            return view.max_contribution
        return 0


class FixedZeroPolicy(JointProjectPolicy):
    """Fixed, non-learning free-rider: never contributes."""

    variant_id = "fixed_zero"

    def choose_pledge(self, view: AgentView) -> int:
        return 0

    def choose_contribution(self, view: AgentView) -> int:
        return 0


class MemoryPolicy(JointProjectPolicy):
    """Win-stay / lose-shift on the public record.  No belief, no cost model."""

    variant_id = "memory"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.uses_memory = True

    def _previous_own_contribution(self, view: AgentView) -> int | None:
        if not view.public_history:
            return None
        last = view.public_history[-1]
        return dict(last.contributions).get(self.agent_id)

    def choose_pledge(self, view: AgentView) -> int:
        return self._plan(view)

    def choose_contribution(self, view: AgentView) -> int:
        return self._plan(view)

    def _plan(self, view: AgentView) -> int:
        previous = self._previous_own_contribution(view)
        if previous is None:
            return min(view.max_contribution, 1)
        if view.public_history[-1].success:
            # The project succeeded; if I contributed nothing, keep free-riding.
            return 0 if previous == 0 else previous
        # It failed: contribute one unit more, up to the maximum.
        return min(view.max_contribution, previous + 1)


class BeliefPolicy(JointProjectPolicy):
    """Bayesian posterior over the joint cost-type vector, then EV maximisation."""

    variant_id = "belief"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.uses_memory = True
        self.uses_belief = True
        self.hypotheses = _type_hypotheses(self.config)
        # The contract makes the type distribution public, so the prior over type
        # vectors is the product of the per-agent probabilities.  A uniform 1/81
        # prior would silently contradict the contract and change the best
        # response, so it is initialised explicitly and pinned by a test.
        self.posterior = [
            _hypothesis_prior(hypothesis, self.config)
            for hypothesis in self.hypotheses
        ]
        self.processed_rounds = 0

    # -- inference -------------------------------------------------------
    def normalised_posterior(self) -> list[float]:
        total = sum(self.posterior)
        if total <= 0:
            raise ValueError("posterior collapsed to zero mass")
        return [value / total for value in self.posterior]

    def marginals(self) -> tuple[tuple[float, ...], ...]:
        """Per-agent marginal distribution over cost types from the posterior."""
        weights = self.normalised_posterior()
        out: list[tuple[float, ...]] = []
        for agent in range(self.config.num_agents):
            row = []
            for value in self.config.type_values:
                row.append(
                    sum(
                        weight
                        for index, weight in enumerate(weights)
                        if self.hypotheses[index][agent] == value
                    )
                )
            out.append(tuple(row))
        return tuple(out)

    def update_from_history(self, view: AgentView) -> None:
        """Exact filtering: a hypothesis survives only if it reproduces the surplus."""
        while self.processed_rounds < len(view.public_history):
            record = view.public_history[self.processed_rounds]
            contributions = [dict(record.contributions)[a] for a in range(self.config.num_agents)]
            for index, hypothesis in enumerate(self.hypotheses):
                if self.posterior[index] <= 0.0:
                    continue
                implied = round_joint_surplus(
                    contributions=contributions,
                    types=hypothesis,
                    config=self.config,
                )
                if implied != record.total_surplus:
                    self.posterior[index] = 0.0
            self.processed_rounds += 1

    def probability_of_success(
        self, view: AgentView, own_contribution: int
    ) -> float:
        """P(project succeeds | my contribution) under the documented rule."""
        weights = self.normalised_posterior()
        probability = 0.0
        for index, hypothesis in enumerate(self.hypotheses):
            weight = weights[index]
            if weight <= 0:
                continue
            others = sum(
                1
                for agent in range(self.config.num_agents)
                if agent != self.agent_id
                and hypothesis[agent] <= PREDICTED_CONTRIBUTOR_COST_CEILING
            )
            total = others * self.config.max_contribution + own_contribution
            if total >= self.config.threshold:
                probability += weight
        return probability

    def best_response(self, view: AgentView) -> int:
        best_value = float("-inf")
        best_action = 0
        best_probability = 0.0
        for action in view.legal_values:
            probability = self.probability_of_success(view, action)
            value = self.config.bonus * probability - view.own_type * action
            if value > best_value:
                best_value = value
                best_action = action
                best_probability = probability
        # Recorded so the harness can measure the model's own optimism instead of
        # the reader having to infer it.
        self.last_success_probability = best_probability
        self.last_expected_value = best_value
        self.last_action = best_action
        return best_action

    # -- protocol --------------------------------------------------------
    def choose_pledge(self, view: AgentView) -> int:
        self.update_from_history(view)
        return self.best_response(view)

    def choose_contribution(self, view: AgentView) -> int:
        self.update_from_history(view)
        return self.best_response(view)


class BeliefPlanningPolicy(BeliefPolicy):
    """Belief plus a one-ply response model conditioned on public pledges.

    Reputation is endogenous in this substrate, so the model treats each other
    agent as honouring its pledge with probability equal to its measured
    pledge-keeping rate, and otherwise falling back to the type rule.
    """

    variant_id = "belief_planning"

    def pledge_reliability(self, view: AgentView, agent_id: int) -> float:
        kept = dict(view.pledges_kept).get(agent_id, 0)
        broken = dict(view.pledges_broken).get(agent_id, 0)
        return (kept + PLEDGE_RELIABILITY_ALPHA) / (
            kept + broken + PLEDGE_RELIABILITY_ALPHA + PLEDGE_RELIABILITY_BETA
        )

    def probability_of_success(
        self, view: AgentView, own_contribution: int
    ) -> float:
        pledges = dict(view.pledges_this_round)
        others = [a for a in range(self.config.num_agents) if a != self.agent_id]
        weights = self.normalised_posterior()
        probability = 0.0
        for index, hypothesis in enumerate(self.hypotheses):
            weight = weights[index]
            if weight <= 0:
                continue
            # Enumerate which of the others honour their pledge.
            for size in range(len(others) + 1):
                for honouring in combinations(others, size):
                    outcome_probability = 1.0
                    for agent in others:
                        reliability = self.pledge_reliability(view, agent)
                        outcome_probability *= (
                            reliability if agent in honouring else 1.0 - reliability
                        )
                    if outcome_probability <= 0:
                        continue
                    total = own_contribution
                    for agent in others:
                        if agent in honouring:
                            total += pledges.get(agent, 0)
                        elif (
                            hypothesis[agent]
                            <= PREDICTED_CONTRIBUTOR_COST_CEILING
                        ):
                            total += self.config.max_contribution
                    if total >= self.config.threshold:
                        probability += weight * outcome_probability
        return probability


POLICY_TYPES: dict[str, type[JointProjectPolicy]] = {
    "plain": JointProjectPolicy,
    "memory": MemoryPolicy,
    "belief": BeliefPolicy,
    "belief_planning": BeliefPlanningPolicy,
    "fixed_cost_threshold": FixedCostThresholdPolicy,
    "fixed_zero": FixedZeroPolicy,
}


def build_policy(
    variant_id: str, *, agent_id: int, config: JointProjectConfig, seed: int
) -> JointProjectPolicy:
    try:
        policy_type = POLICY_TYPES[variant_id]
    except KeyError as exc:
        raise ValueError(f"unknown joint-project policy: {variant_id}") from exc
    return policy_type(agent_id=agent_id, config=config, seed=seed)


# ---------------------------------------------------------------------------
# Episode running and evaluation
# ---------------------------------------------------------------------------


@dataclass
class EpisodeOutcome:
    variant_id: str
    seed: int
    types: tuple[int, ...]
    history: tuple[RoundRecord, ...]
    payoffs: tuple[float, ...]
    brier_samples: list[tuple[float, int]] = field(default_factory=list)
    posterior_mass_on_truth: list[float] = field(default_factory=list)
    believed_success_probability: list[float] = field(default_factory=list)
    pledge_broken: int = 0
    best_response_regrets: list[float] = field(default_factory=list)
    contributions_taken: list[int] = field(default_factory=list)
    steps: int = 0


def run_episode(
    *,
    variant_id: str,
    seed: int,
    config: JointProjectConfig | None = None,
    episode_policy_classes: Mapping[int, str] | None = None,
) -> EpisodeOutcome:
    """Play one episode.

    ``episode_policy_classes`` overrides which policy drives which agent, which is
    how a mixed table with a fixed alternative opponent is built.  The mapping is
    experiment design and never reaches a policy, which still only sees its own
    AgentView.
    """
    config = config or JointProjectConfig()
    env = JointProjectEnv(config=config)
    env.reset(seed=seed)
    seat_variant = {
        agent: (
            episode_policy_classes.get(agent, variant_id)
            if episode_policy_classes
            else variant_id
        )
        for agent in range(config.num_agents)
    }
    policies = {
        agent: build_policy(
            seat_variant[agent],
            agent_id=agent,
            config=config,
            seed=seed * 1000 + agent,
        )
        for agent in range(config.num_agents)
    }
    outcome = EpisodeOutcome(
        variant_id=variant_id,
        seed=seed,
        types=env.true_types(),
        history=(),
        payoffs=(),
    )

    while not env.done:
        views = {agent: env.observe(agent) for agent in range(config.num_agents)}
        actions = {agent: policies[agent].act(views[agent]) for agent in range(config.num_agents)}
        if env.phase == PHASE_CONTRIBUTE:
            for agent in range(config.num_agents):
                outcome.contributions_taken.append(actions[agent])
        env.resolve(actions)
        outcome.steps += 1
        # Snapshots for calibration, taken while the episode is in progress so a
        # later update cannot rewrite an earlier reading.
        for agent in range(config.num_agents):
            policy = policies[agent]
            if not getattr(policy, "uses_belief", False):
                continue
            weights = policy.normalised_posterior()
            truth = tuple(
                int(cost) for cost in outcome.types
            )
            truth_index = policy.hypotheses.index(truth)
            outcome.posterior_mass_on_truth.append(weights[truth_index])
            if hasattr(policy, "last_success_probability"):
                outcome.believed_success_probability.append(
                    float(policy.last_success_probability)
                )
            marginals = policy.marginals()
            for other in range(config.num_agents):
                if other == agent:
                    continue
                for value, probability in zip(config.type_values, marginals[other]):
                    outcome.brier_samples.append(
                        (probability, 0 if value == outcome.types[other] else 1)
                    )

    outcome.history = env.history
    outcome.payoffs = tuple(env.total_payoffs()[a] for a in range(config.num_agents))
    outcome.pledge_broken = sum(len(record.pledge_broken) for record in env.history)
    outcome.best_response_regrets = _best_response_regrets(env, config)
    return outcome


def _best_response_regrets(
    env: JointProjectEnv, config: JointProjectConfig
) -> list[float]:
    """Legitimate post-hoc counterfactual regret, diagnostic only.

    The counterfactual recomputes the success flag for the alternative action
    instead of reusing the observed one, because whether the project succeeds
    depends on the agent's own contribution.
    """
    regrets: list[float] = []
    types = env.true_types()
    for record in env.history:
        contributions = dict(record.contributions)
        for agent in range(config.num_agents):
            others = [
                contributions[other]
                for other in range(config.num_agents)
                if other != agent
            ]
            base = sum(others)
            actual_x = contributions[agent]
            actual_success = base + actual_x >= config.threshold
            actual = (
                (config.bonus if actual_success else 0.0)
                - types[agent] * actual_x
            )
            best_x = best_own_contribution_given_realised_others(
                own_type=types[agent],
                others_contributions=others,
                config=config,
            )
            best_success = base + best_x >= config.threshold
            best = (
                (config.bonus if best_success else 0.0) - types[agent] * best_x
            )
            regrets.append(best - actual)
    return regrets


def _prior_mass_on_truth(outcome: EpisodeOutcome, config: JointProjectConfig) -> float:
    """What the posterior mass on the truth would be with no evidence at all.

    The hypothesis space has ``len(type_values)**num_agents`` vectors, so mass
    near the uniform value ``1/size`` means the belief learned nothing.
    """
    mass = 1.0
    for cost in outcome.types:
        mass *= config.type_probabilities[config.type_values.index(int(cost))]
    return mass


def brier_score(samples: Sequence[tuple[float, int]]) -> float | None:
    if not samples:
        return None
    return sum((probability - outcome) ** 2 for probability, outcome in samples) / len(
        samples
    )


def evaluate_episode(outcome: EpisodeOutcome, config: JointProjectConfig) -> dict[str, Any]:
    """Score one episode.  Truth is consumed only here and in the labels above."""
    optima: list[float] = []
    achieved: list[float] = []
    abandonment_rounds = 0
    pareto_rounds = 0
    for record in outcome.history:
        types = list(outcome.types)
        optimum, _plan = full_information_optimum(types=types, config=config)
        optima.append(optimum)
        achieved.append(record.total_surplus)
        if optimum <= 0:
            abandonment_rounds += 1
        if record.total_surplus == optimum:
            pareto_rounds += 1
    informative = [
        (a / o) for a, o in zip(achieved, optima) if o > 0
    ]
    efficiency = sum(informative) / len(informative) if informative else None
    return {
        "variant_id": outcome.variant_id,
        "seed": outcome.seed,
        "types": list(outcome.types),
        "payoffs": [float(x) for x in outcome.payoffs],
        "social_utility": float(sum(outcome.payoffs)),
        "mean_payoff": float(sum(outcome.payoffs)) / len(outcome.payoffs),
        "rounds": len(outcome.history),
        "successful_rounds": sum(1 for record in outcome.history if record.success),
        "achieved_surplus": float(sum(achieved)),
        "full_information_surplus": float(sum(optima)),
        "joint_surplus_efficiency": efficiency,
        "pareto_optimal_rounds": pareto_rounds,
        "abandonment_rounds": abandonment_rounds,
        "mean_brier_type_inference": brier_score(outcome.brier_samples),
        "mean_posterior_mass_on_truth": (
            sum(outcome.posterior_mass_on_truth)
            / len(outcome.posterior_mass_on_truth)
            if outcome.posterior_mass_on_truth
            else None
        ),
        "prior_mass_on_truth_baseline": _prior_mass_on_truth(outcome, config),
        "mean_believed_success_probability": (
            sum(outcome.believed_success_probability)
            / len(outcome.believed_success_probability)
            if outcome.believed_success_probability
            else None
        ),
        "actual_success_rate": (
            sum(1 for record in outcome.history if record.success)
            / len(outcome.history)
            if outcome.history
            else None
        ),
        "contribution_histogram": {
            str(value): outcome.contributions_taken.count(value)
            for value in config.legal_values
        },
        "pledge_violations": outcome.pledge_broken,
        "mean_best_response_regret_diagnostic": (
            sum(outcome.best_response_regrets) / len(outcome.best_response_regrets)
            if outcome.best_response_regrets
            else None
        ),
        "information_leakage_count": 0,
    }


def mechanism_diagnostics(
    outcomes: Sequence[EpisodeOutcome], config: JointProjectConfig
) -> dict[str, Any]:
    """Interpretable mechanisms behind any utility difference.

    The peer's mechanism gate requires that a gain be attributed rather than
    assumed, because the SecretMafia cross-play gain turned out to be an artifact
    of mirrored deterministic agents.
    """
    contribution_by_own_type: dict[int, list[int]] = {}
    coalition_rounds = 0
    coalition_success_rounds = 0
    total_rounds = 0
    pledge_honoured = 0
    pledge_total = 0
    for outcome in outcomes:
        for record in outcome.history:
            contributions = dict(record.contributions)
            total_rounds += 1
            for agent in range(config.num_agents):
                contribution_by_own_type.setdefault(outcome.types[agent], []).append(
                    contributions[agent]
                )
            # Which agents could profitably carry the load?
            cheap = [
                agent
                for agent in range(config.num_agents)
                if outcome.types[agent] <= PREDICTED_CONTRIBUTOR_COST_CEILING
            ]
            cheap_contributed = sum(
                1 for agent in cheap if contributions[agent] > 0
            )
            if len(cheap) >= 2:
                coalition_rounds += 1
                if cheap_contributed == len(cheap):
                    if record.success:
                        coalition_success_rounds += 1
            for agent, pledged in record.pledges:
                pledge_total += 1
                if pledged == contributions[agent]:
                    pledge_honoured += 1

    def mean_for(cost: int) -> float | None:
        values = contribution_by_own_type.get(cost)
        return sum(values) / len(values) if values else None

    return {
        "mean_contribution_by_own_type": {
            str(cost): mean_for(cost) for cost in config.type_values
        },
        "contribution_type_association_note": (
            "A contingent policy contributes more when its own cost is low. If these "
            "means are all equal, the policy is not conditioning on its private type."
        ),
        "cheap_coalition_rounds": coalition_rounds,
        "cheap_coalition_full_participation_success_rate": (
            coalition_success_rounds / coalition_rounds if coalition_rounds else None
        ),
        "cheap_coalition_note": (
            "Rounds where at least two agents are cheap enough to carry the project. "
            "A strategy that fails to use them is leaving surplus on the table."
        ),
        "pledge_honour_rate": (
            pledge_honoured / pledge_total if pledge_total else None
        ),
        "rounds_observed": total_rounds,
    }


def run_smoke_ab(
    *,
    variants: Sequence[str] = ("plain", "memory", "belief", "belief_planning"),
    episodes: int = 30,
    config: JointProjectConfig | None = None,
    mixed_table: Mapping[int, str] | None = None,
    progress: bool = False,
) -> dict[str, Any]:
    config = config or JointProjectConfig()
    seeds = list(range(episodes))
    variant_rows: dict[str, Any] = {}
    all_outcomes: dict[str, list[EpisodeOutcome]] = {}
    for variant_id in variants:
        started = time.perf_counter()
        outcomes = [
            run_episode(variant_id=variant_id, seed=seed, config=config)
            for seed in seeds
        ]
        elapsed = time.perf_counter() - started
        reports = [evaluate_episode(outcome, config) for outcome in outcomes]
        all_outcomes[variant_id] = outcomes
        variant_rows[variant_id] = {
            "episodes": len(reports),
            "mean_social_utility": _mean([r["social_utility"] for r in reports]),
            "mean_payoff_per_agent": _mean([r["mean_payoff"] for r in reports]),
            "mean_successful_rounds": _mean(
                [float(r["successful_rounds"]) for r in reports]
            ),
            "mean_joint_surplus_efficiency": _mean(
                [
                    r["joint_surplus_efficiency"]
                    for r in reports
                    if r["joint_surplus_efficiency"] is not None
                ]
            ),
            "mean_achieved_surplus": _mean([r["achieved_surplus"] for r in reports]),
            "mean_full_information_surplus": _mean(
                [r["full_information_surplus"] for r in reports]
            ),
            "pareto_optimal_rounds": sum(r["pareto_optimal_rounds"] for r in reports),
            "abandonment_rounds": sum(r["abandonment_rounds"] for r in reports),
            "mean_brier_type_inference": _mean(
                [
                    r["mean_brier_type_inference"]
                    for r in reports
                    if r["mean_brier_type_inference"] is not None
                ]
            ),
            "mean_posterior_mass_on_truth": _mean(
                [
                    r["mean_posterior_mass_on_truth"]
                    for r in reports
                    if r["mean_posterior_mass_on_truth"] is not None
                ]
            ),
            "mean_prior_mass_on_truth_baseline": _mean(
                [r["prior_mass_on_truth_baseline"] for r in reports]
            ),
            "mean_believed_success_probability": _mean(
                [
                    r["mean_believed_success_probability"]
                    for r in reports
                    if r["mean_believed_success_probability"] is not None
                ]
            ),
            "mean_actual_success_rate": _mean(
                [
                    r["actual_success_rate"]
                    for r in reports
                    if r["actual_success_rate"] is not None
                ]
            ),
            "contribution_histogram": _merge_histograms(
                [r["contribution_histogram"] for r in reports], config
            ),
            "pledge_violations": sum(r["pledge_violations"] for r in reports),
            "mean_best_response_regret_diagnostic": _mean(
                [
                    r["mean_best_response_regret_diagnostic"]
                    for r in reports
                    if r["mean_best_response_regret_diagnostic"] is not None
                ]
            ),
            "information_leakage_count": sum(
                r["information_leakage_count"] for r in reports
            ),
            "wall_clock_seconds": elapsed,
            "mechanism_diagnostics": mechanism_diagnostics(outcomes, config),
        }
        if progress:
            print(f"  {variant_id}: done in {elapsed:.1f}s", flush=True)

    mixed_rows = None
    if mixed_table:
        outcomes = [
            run_episode(
                variant_id="mixed_table",
                seed=seed,
                config=config,
                episode_policy_classes=mixed_table,
            )
            for seed in seeds
        ]
        reports = [evaluate_episode(outcome, config) for outcome in outcomes]
        mixed_rows = {
            "seat_policy": {str(k): v for k, v in sorted(mixed_table.items())},
            "episodes": len(reports),
            "mean_social_utility": _mean([r["social_utility"] for r in reports]),
            "mean_joint_surplus_efficiency": _mean(
                [
                    r["joint_surplus_efficiency"]
                    for r in reports
                    if r["joint_surplus_efficiency"] is not None
                ]
            ),
            "mean_best_response_regret_diagnostic": _mean(
                [
                    r["mean_best_response_regret_diagnostic"]
                    for r in reports
                    if r["mean_best_response_regret_diagnostic"] is not None
                ]
            ),
            "mechanism_diagnostics": mechanism_diagnostics(outcomes, config),
        }

    return {
        "schema_version": 1,
        "status": "smoke_ab_run",
        "historical_world_writeback": False,
        "evidence_class": (
            "own-authored substrate smoke A/B, per peer decision "
            "2026-10-11-0021. The environment is authored by this project, so this "
            "is weaker evidence than a third-party benchmark and is labelled as such."
        ),
        "contract": "docs/adaptation/sck-mixed-motive-benchmark-contract-v1.md",
        "design": {
            "episodes_per_variant": episodes,
            "seeds": seeds,
            "config": {
                "num_agents": config.num_agents,
                "rounds": config.rounds,
                "threshold": config.threshold,
                "bonus": config.bonus,
                "max_contribution": config.max_contribution,
                "type_values": list(config.type_values),
                "type_probabilities": list(config.type_probabilities),
            },
            "variants": list(variants),
            "fixed_alternative_policy": "fixed_cost_threshold",
            "same_seed_schedule_for_every_variant": True,
        },
        "variants": variant_rows,
        "mixed_table": mixed_rows,
        "reading_notes": [
            "Primary outcome is social utility and joint-surplus efficiency against the exact full-information optimum, not a win rate.",
            "mean_best_response_regret_diagnostic is a secondary diagnostic only, computed against a legitimate post-hoc counterfactual, never the acceptance metric.",
            "Information leakage is structurally zero here: the only private fact is the cost type, and disclosing it is a legal strategic choice rather than a leak. It is reported as such rather than as an achievement.",
            "Any utility difference must be attributed by mechanism_diagnostics before it is called a cognition gain.",
        ],
    }


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _merge_histograms(
    histograms: Sequence[Mapping[str, int]], config: JointProjectConfig
) -> dict[str, int]:
    merged = {str(value): 0 for value in config.legal_values}
    for histogram in histograms:
        for key, count in histogram.items():
            merged[key] = merged.get(key, 0) + int(count)
    return merged


def format_smoke_ab(report: dict[str, Any]) -> str:
    def fmt(value, spec=".3f"):
        return "n/a" if value is None else format(value, spec)

    lines = [
        "SCK mixed-motive Joint Project smoke A/B",
        f"  episodes per variant : {report['design']['episodes_per_variant']}",
        f"  agents / rounds      : {report['design']['config']['num_agents']} / {report['design']['config']['rounds']}",
        "",
        f"  {'variant':<18}{'social':>9}{'effic.':>8}{'succ.rnd':>10}{'brier':>8}{'post.':>7}{'viol':>6}{'regret':>8}",
    ]
    for variant_id, row in report["variants"].items():
        lines.append(
            f"  {variant_id:<18}"
            f"{fmt(row['mean_social_utility'], '.2f'):>9}"
            f"{fmt(row['mean_joint_surplus_efficiency']):>8}"
            f"{fmt(row['mean_successful_rounds'], '.2f'):>10}"
            f"{fmt(row['mean_brier_type_inference']):>8}"
            f"{fmt(row['mean_posterior_mass_on_truth']):>7}"
            f"{row['pledge_violations']:>6}"
            f"{fmt(row['mean_best_response_regret_diagnostic']):>8}"
        )
    lines.append("")
    lines.append("  social = mean social utility; effic. = achieved / full-information optimum")
    lines.append("  brier  = type-inference Brier (lower better); post. = posterior mass on truth")
    lines.append("  regret = best-response counterfactual, DIAGNOSTIC ONLY")
    lines.append("")
    lines.append("  mechanism: is the belief learning, and is the model calibrated?")
    lines.append(
        f"  {'variant':<18}{'post.':>8}{'prior':>8}{'believed P':>12}{'actual':>8}{'contrib=0':>11}"
    )
    for variant_id, row in report["variants"].items():
        histogram = row["contribution_histogram"]
        total = sum(histogram.values()) or 1
        lines.append(
            f"  {variant_id:<18}"
            f"{fmt(row['mean_posterior_mass_on_truth']):>8}"
            f"{fmt(row['mean_prior_mass_on_truth_baseline']):>8}"
            f"{fmt(row['mean_believed_success_probability']):>12}"
            f"{fmt(row['mean_actual_success_rate']):>8}"
            f"{histogram.get('0', 0) / total:>11.2f}"
        )
    lines.append("")
    lines.append("  plain/prior = posterior mass on the true type vector with no evidence;")
    lines.append("  a posterior equal to the prior means the belief learned nothing.")
    lines.append("")
    lines.append("  mechanism: mean contribution by own cost type")
    for variant_id, row in report["variants"].items():
        diag = row["mechanism_diagnostics"]
        by_type = ", ".join(
            f"c{k}={fmt(v, '.2f')}"
            for k, v in diag["mean_contribution_by_own_type"].items()
        )
        lines.append(
            f"  {variant_id:<18}{by_type:<34}"
            f"pledge_honour={fmt(diag['pledge_honour_rate'])}"
        )
    if report.get("mixed_table"):
        mixed = report["mixed_table"]
        lines.append("")
        lines.append(
            f"  mixed table {mixed['seat_policy']}: social={fmt(mixed['mean_social_utility'], '.2f')}"
            f" effic={fmt(mixed['mean_joint_surplus_efficiency'])}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument(
        "--variants",
        default="plain,memory,belief,belief_planning",
        help="Comma-separated variant ids.",
    )
    parser.add_argument(
        "--mixed-belief-seats",
        type=int,
        default=2,
        help=(
            "How many seats run belief_planning in the mixed table against the "
            "fixed cost-threshold policy. 0 disables the mixed table."
        ),
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    config = JointProjectConfig()
    mixed_table = None
    if args.mixed_belief_seats:
        mixed_table = {
            agent: (
                "belief_planning"
                if agent < args.mixed_belief_seats
                else "fixed_cost_threshold"
            )
            for agent in range(config.num_agents)
        }

    report = run_smoke_ab(
        variants=tuple(v.strip() for v in args.variants.split(",") if v.strip()),
        episodes=args.episodes,
        config=config,
        mixed_table=mixed_table,
        progress=not args.quiet,
    )
    print(format_smoke_ab(report))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
