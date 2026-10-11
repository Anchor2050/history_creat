"""Tests for the SCK harness on the mixed-motive Joint Project substrate.

No textarena dependency: the substrate is local and deterministic.
"""
import ast
import inspect

import pytest

from narrative.longform import sck_joint_project_harness_v1 as h
from narrative.longform.sck_joint_project_env_v1 import (
    PHASE_CONTRIBUTE,
    PHASE_PLEDGE,
    JointProjectConfig,
    JointProjectEnv,
)


def test_unknown_policy_is_rejected_and_every_contract_variant_builds():
    config = JointProjectConfig()
    for variant_id in ("plain", "memory", "belief", "belief_planning",
                       "fixed_cost_threshold", "fixed_zero"):
        policy = h.build_policy(variant_id, agent_id=0, config=config, seed=1)
        assert policy.agent_id == 0
    with pytest.raises(ValueError):
        h.build_policy("mcts", agent_id=0, config=config, seed=1)


def test_fixed_policies_are_non_adaptive_by_construction():
    config = JointProjectConfig()
    zero = h.build_policy("fixed_zero", agent_id=0, config=config, seed=1)
    threshold = h.build_policy("fixed_cost_threshold", agent_id=0, config=config, seed=1)
    assert zero.uses_memory is False and zero.uses_belief is False
    assert threshold.uses_memory is False and threshold.uses_belief is False


def test_fixed_zero_never_contributes_and_never_pledges():
    outcome = h.run_episode(variant_id="fixed_zero", seed=3)
    assert set(outcome.contributions_taken) == {0}
    assert all(record.pledges == tuple((a, 0) for a in range(4)) for record in outcome.history)
    assert outcome.pledge_broken == 0
    assert outcome.payoffs == (0.0, 0.0, 0.0, 0.0)


def test_fixed_cost_threshold_follows_the_contract_reference_rule():
    outcome = h.run_episode(variant_id="fixed_cost_threshold", seed=5)
    expected = [
        outcome.history[0].contributions[a][1]
        for a in range(4)
    ]
    for agent in range(4):
        want = 3 if outcome.types[agent] <= 2 else 0
        assert expected[agent] == want or True  # per-round check follows
    for record in outcome.history:
        contributions = dict(record.contributions)
        for agent in range(4):
            want = 3 if outcome.types[agent] <= 2 else 0
            assert contributions[agent] == want


def test_an_episode_is_deterministic_for_a_fixed_seed():
    first = h.run_episode(variant_id="belief_planning", seed=7)
    second = h.run_episode(variant_id="belief_planning", seed=7)
    assert first.types == second.types
    assert first.payoffs == second.payoffs
    assert first.contributions_taken == second.contributions_taken


def test_mixed_table_runs_the_specified_policy_on_each_seat():
    config = JointProjectConfig()
    table = {0: "belief", 1: "fixed_zero", 2: "fixed_zero", 3: "fixed_zero"}
    outcome = h.run_episode(
        variant_id="mixed", seed=4, config=config, episode_policy_classes=table
    )
    # Seats 1-3 never contribute, so the project can only fail.
    for record in outcome.history:
        contributions = dict(record.contributions)
        assert contributions[1] == contributions[2] == contributions[3] == 0
        assert record.success is False
    # A single agent cannot reach a threshold of 6 with a maximum of 3.
    assert outcome.payoffs[1] == 0.0


def test_belief_posterior_learns_from_aggregate_surplus_only():
    config = JointProjectConfig()
    policy = h.build_policy("belief", agent_id=0, config=config, seed=0)
    env = JointProjectEnv(config=config)
    env.reset(seed=11)
    truth_index = policy.hypotheses.index(env.true_types())
    prior = policy.normalised_posterior()[truth_index]
    # Two informative rounds give two linear equations.
    for contributions in ({a: 3 for a in range(4)}, {a: 0 for a in range(4)}):
        env.resolve({a: 1 for a in range(4)})
        env.resolve(contributions)
        policy.update_from_history(env.observe(0))
    posterior = policy.normalised_posterior()
    assert posterior[truth_index] > 0
    assert sum(posterior) == pytest.approx(1.0)
    assert posterior[truth_index] >= prior


def test_marginals_are_normalised_and_cover_the_type_values():
    config = JointProjectConfig()
    policy = h.build_policy("belief", agent_id=2, config=config, seed=0)
    marginals = policy.marginals()
    assert len(marginals) == config.num_agents
    for row in marginals:
        assert len(row) == len(config.type_values)
        assert sum(row) == pytest.approx(1.0)


def test_belief_prior_is_the_contract_distribution_not_a_uniform_one():
    """A uniform 1/81 prior would contradict the contract and change the response."""
    config = JointProjectConfig()
    policy = h.build_policy("belief", agent_id=0, config=config, seed=0)
    weights = policy.normalised_posterior()
    assert len(weights) == len(config.type_values) ** config.num_agents
    uniform = 1.0 / len(weights)
    for hypothesis, weight in zip(policy.hypotheses, weights):
        expected = h._hypothesis_prior(hypothesis, config)
        assert weight == pytest.approx(expected)
    # The prior must not be flat: a cheap-heavy vector is more likely than an
    # expensive-heavy one.
    cheap_vector = (1, 1, 1, 1)
    expensive_vector = (4, 4, 4, 4)
    assert weights[policy.hypotheses.index(cheap_vector)] > uniform
    assert weights[policy.hypotheses.index(expensive_vector)] < uniform
    assert weights[policy.hypotheses.index(cheap_vector)] > weights[
        policy.hypotheses.index(expensive_vector)
    ]


def test_an_uninformative_round_leaves_the_posterior_exactly_at_the_prior():
    """All-zero contributions carry no information, which is the measured trap."""
    config = JointProjectConfig()
    policy = h.build_policy("belief", agent_id=0, config=config, seed=0)
    env = JointProjectEnv(config=config)
    env.reset(seed=2)
    before = policy.normalised_posterior()
    truth_index = policy.hypotheses.index(env.true_types())
    env.resolve({a: 0 for a in range(4)})
    env.resolve({a: 0 for a in range(4)})
    policy.update_from_history(env.observe(0))
    after = policy.normalised_posterior()
    assert after[truth_index] == pytest.approx(before[truth_index])
    assert after == pytest.approx(before)


def test_an_informative_round_raises_the_posterior_mass_on_the_truth():
    config = JointProjectConfig()
    policy = h.build_policy("belief", agent_id=0, config=config, seed=0)
    env = JointProjectEnv(config=config)
    env.reset(seed=15)
    truth_index = policy.hypotheses.index(env.true_types())
    before = policy.normalised_posterior()[truth_index]
    env.resolve({a: 1 for a in range(4)})
    env.resolve({0: 3, 1: 0, 2: 2, 3: 1})
    policy.update_from_history(env.observe(0))
    after = policy.normalised_posterior()[truth_index]
    assert after > before


def test_the_belief_agent_free_rides_when_it_expects_two_cheap_partners():
    """Pins the mechanism the smoke A/B measures, not just its number.

    With the prior, three others are each cheap with probability 0.8, so two or
    more contributors are likely and the project succeeds even if this agent
    contributes nothing.  Maximising expected value then means contributing
    nothing, which is also what starves the agent's own evidence channel.
    """
    config = JointProjectConfig()
    policy = h.build_policy("belief", agent_id=0, config=config, seed=0)
    env = JointProjectEnv(config=config)
    env.reset(seed=2)
    view = env.observe(0)
    assert policy.choose_contribution(view) == 0
    assert policy.last_success_probability > 0.5


def test_pledge_conditioning_lowers_the_believed_success_probability():
    """belief_planning reacts to the public pledge record, belief does not."""
    config = JointProjectConfig()
    env = JointProjectEnv(config=config)
    env.reset(seed=8)
    plain_belief = h.build_policy("belief", agent_id=0, config=config, seed=0)
    planner = h.build_policy("belief_planning", agent_id=0, config=config, seed=0)
    # Everyone pledges zero, which is the strongest possible signal of no help.
    env.resolve({a: 0 for a in range(4)})
    view = env.observe(0)
    assert planner.probability_of_success(view, 0) < plain_belief.probability_of_success(
        view, 0
    )


def test_pledge_reliability_starts_at_the_documented_prior_and_moves_with_history():
    config = JointProjectConfig()
    planner = h.build_policy("belief_planning", agent_id=0, config=config, seed=0)
    env = JointProjectEnv(config=config)
    env.reset(seed=6)
    fresh = planner.pledge_reliability(env.observe(0), 1)
    assert fresh == pytest.approx(h.PLEDGE_RELIABILITY_PRIOR)
    # Seat 1 pledges 3 and contributes 3 for two rounds: reliability rises.
    for _ in range(2):
        env.resolve({0: 0, 1: 3, 2: 0, 3: 0})
        env.resolve({0: 0, 1: 3, 2: 0, 3: 0})
    assert planner.pledge_reliability(env.observe(0), 1) > fresh


def test_evaluation_reports_efficiency_within_bounds_and_counts_pareto_rounds():
    config = JointProjectConfig()
    outcome = h.run_episode(variant_id="fixed_cost_threshold", seed=13)
    report = h.evaluate_episode(outcome, config)
    assert 0.0 <= report["joint_surplus_efficiency"] <= 1.0
    assert report["pareto_optimal_rounds"] <= report["rounds"]
    assert report["rounds"] == config.rounds
    assert report["abandonment_rounds"] >= 0
    assert report["information_leakage_count"] == 0


def test_best_response_regret_is_zero_when_no_unilateral_move_can_succeed():
    """With threshold 6 and a maximum of 3, one agent cannot rescue a total of 0."""
    config = JointProjectConfig()
    env = JointProjectEnv(config=config)
    env.reset(seed=1)
    env.resolve({a: 0 for a in range(4)})
    env.resolve({a: 0 for a in range(4)})
    assert h._best_response_regrets(env, config) == [0.0, 0.0, 0.0, 0.0]


def test_best_response_regret_recomputes_success_instead_of_reusing_it():
    """A one-unit shortfall must show regret, whatever the agent's cost type."""
    config = JointProjectConfig()
    env = JointProjectEnv(config=config)
    env.reset(seed=1)
    # Total 5 < 6, so the round fails; agent 0 contributed nothing and its own
    # one extra unit would have made the project succeed.  Reusing the observed
    # success flag would wrongly report zero regret.
    contributions = {0: 0, 1: 3, 2: 2, 3: 0}
    env.resolve({a: 1 for a in range(4)})
    env.resolve(contributions)
    regrets = h._best_response_regrets(env, config)
    agent_zero_type = env.true_types()[0]
    expected = float(config.bonus) - agent_zero_type * 1
    assert regrets[0] == pytest.approx(expected)
    assert regrets[0] > 0.0


def test_mechanism_diagnostics_reports_type_association_and_pledge_honour():
    config = JointProjectConfig()
    outcomes = [
        h.run_episode(variant_id="fixed_cost_threshold", seed=seed)
        for seed in range(3)
    ]
    diag = h.mechanism_diagnostics(outcomes, config)
    by_type = diag["mean_contribution_by_own_type"]
    # The fixed rule contributes 3 for cheap types and 0 for expensive ones.
    assert by_type["1"] == 3.0
    assert by_type["2"] == 3.0
    assert by_type["4"] == 0.0
    assert diag["pledge_honour_rate"] == 1.0
    assert diag["rounds_observed"] == 3 * config.rounds


def test_smoke_ab_reports_design_metrics_and_labelled_limits():
    report = h.run_smoke_ab(
        variants=("fixed_zero", "fixed_cost_threshold"),
        episodes=2,
        mixed_table={0: "belief_planning", 1: "fixed_cost_threshold",
                     2: "fixed_cost_threshold", 3: "fixed_cost_threshold"},
    )
    assert report["design"]["same_seed_schedule_for_every_variant"] is True
    assert report["design"]["episodes_per_variant"] == 2
    assert set(report["variants"]) == {"fixed_zero", "fixed_cost_threshold"}
    assert report["variants"]["fixed_zero"]["mean_social_utility"] == 0.0
    assert report["variants"]["fixed_cost_threshold"]["mean_social_utility"] > 0.0
    assert report["evidence_class"].startswith("own-authored substrate")
    assert report["mixed_table"] is not None
    assert "not a win rate" in " ".join(report["reading_notes"])


def test_policy_classes_never_read_environment_truth():
    """Static audit: no decision-path class touches the type vector."""
    tree = ast.parse(inspect.getsource(h))
    forbidden = {"types", "true_types", "_types", "full_information_optimum"}
    offenders = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.endswith("Policy"):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and child.attr in forbidden:
                offenders.append(f"{node.name}:{child.attr}")
            if (
                isinstance(child, ast.Subscript)
                and isinstance(child.slice, ast.Constant)
                and child.slice.value in forbidden
            ):
                offenders.append(f"{node.name}[{child.slice.value}]")
    assert offenders == [], f"policy read environment truth: {offenders}"


def test_run_episode_rejects_an_unknown_variant():
    with pytest.raises(ValueError):
        h.run_episode(variant_id="not_a_policy", seed=1)
