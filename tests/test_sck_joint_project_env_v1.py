"""Tests for the mixed-motive Joint Project substrate.

These verify the benchmark contract in
``docs/adaptation/sck-mixed-motive-benchmark-contract-v1.md``: fixed parameters,
simultaneous phases, the documented payoff tensions, private persistent cost
types, public pledge/reputation records, determinism, and the information
boundary.
"""
import ast
import inspect
import json

import pytest

from narrative.longform import sck_joint_project_env_v1 as jp
from narrative.longform.sck_joint_project_env_v1 import (
    JointProjectConfig,
    JointProjectEnv,
    JointProjectError,
)


def _drain_episode(env, action_for):
    """Play a whole episode with a caller-supplied action function."""
    while not env.done:
        views = {a: env.observe(a) for a in range(env.config.num_agents)}
        env.resolve({a: action_for(views[a]) for a in range(env.config.num_agents)})
    return env


# ---------------------------------------------------------------------------
# Contract-fixed parameters
# ---------------------------------------------------------------------------


def test_contract_parameters_are_frozen():
    config = JointProjectConfig()
    assert (config.num_agents, config.rounds) == (4, 8)
    assert (config.threshold, config.bonus, config.max_contribution) == (6, 6, 3)
    assert config.type_values == (1, 2, 4)
    assert config.type_probabilities == (0.4, 0.4, 0.2)
    assert config.legal_values == (0, 1, 2, 3)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"num_agents": 3},
        {"rounds": 5},
        {"threshold": 5},
        {"bonus": 9},
        {"max_contribution": 2},
        {"type_values": (1, 2)},
        {"type_probabilities": (0.5, 0.5, 0.0)},
    ],
)
def test_changing_a_contract_parameter_requires_a_new_contract_version(kwargs):
    with pytest.raises(JointProjectError):
        JointProjectConfig(**kwargs)


# ---------------------------------------------------------------------------
# Payoff arithmetic and the documented tensions
# ---------------------------------------------------------------------------


def _surplus(contributions, types):
    return jp.round_joint_surplus(
        contributions=contributions, types=types, config=JointProjectConfig()
    )


def test_all_zero_contributions_fail_and_pay_nothing():
    assert _surplus([0, 0, 0, 0], [1, 1, 4, 4]) == 0.0


def test_cheap_agents_can_reach_the_threshold_profitably():
    # Contract example: types (1,1,4,4) with plan (3,3,0,0) yields joint 18.
    assert _surplus([3, 3, 0, 0], [1, 1, 4, 4]) == 18.0


def test_over_contributing_destroys_value_even_though_the_project_succeeds():
    # Contract example: the same types with plan (3,3,3,3) yield joint -6.
    assert _surplus([3, 3, 3, 3], [1, 1, 4, 4]) == -6.0


def test_an_all_expensive_group_should_abandon_the_project():
    value, plan = jp.full_information_optimum(
        types=[4, 4, 4, 4], config=JointProjectConfig()
    )
    assert value == 0.0
    assert plan == (0, 0, 0, 0)


def test_full_information_optimum_is_exact_and_beats_every_other_plan():
    config = JointProjectConfig()
    types = [1, 2, 4, 1]
    value, plan = jp.full_information_optimum(types=types, config=config)
    assert _surplus(plan, types) == value
    from itertools import product

    for candidate in product(config.legal_values, repeat=config.num_agents):
        assert _surplus(candidate, types) <= value


def test_best_own_contribution_uses_only_post_hoc_realised_information():
    config = JointProjectConfig()
    # Own type 4 (expensive), others already contributed 6, so the project
    # succeeds without this agent: contributing anything only burns its own cost.
    assert (
        jp.best_own_contribution_given_realised_others(
            own_type=4, others_contributions=[3, 3, 0], config=config
        )
        == 0
    )
    # Own type 1 (cheap), others contributed 4, so 2 units secure a bonus of 6
    # for a cost of 2: contributing is worth it.
    assert (
        jp.best_own_contribution_given_realised_others(
            own_type=1, others_contributions=[2, 2, 0], config=config
        )
        == 2
    )


# ---------------------------------------------------------------------------
# Phases and simultaneity
# ---------------------------------------------------------------------------


def test_each_round_runs_a_pledge_phase_then_a_contribution_phase():
    env = JointProjectEnv()
    env.reset(seed=3)
    assert env.phase == jp.PHASE_PLEDGE
    assert env.round_index == 0
    env.resolve({a: 1 for a in range(4)})
    assert env.phase == jp.PHASE_CONTRIBUTE
    assert env.round_index == 0
    env.resolve({a: 1 for a in range(4)})
    assert env.phase == jp.PHASE_PLEDGE
    assert env.round_index == 1
    assert len(env.history) == 1


def test_pledges_become_public_before_the_contribution_choice():
    env = JointProjectEnv()
    env.reset(seed=5)
    env.resolve({0: 3, 1: 2, 2: 1, 3: 0})
    view = env.observe(0)
    assert dict(view.pledges_this_round) == {0: 3, 1: 2, 2: 1, 3: 0}
    # But no contribution of the current round is visible yet.
    assert view.public_history == ()


def test_a_phase_requires_exactly_one_action_per_agent():
    env = JointProjectEnv()
    env.reset(seed=1)
    with pytest.raises(JointProjectError):
        env.resolve({0: 1})
    with pytest.raises(JointProjectError):
        env.resolve({0: 1, 1: 1, 2: 1, 3: 1, 4: 1})


def test_out_of_range_actions_are_rejected_not_silently_clamped():
    env = JointProjectEnv()
    env.reset(seed=1)
    with pytest.raises(JointProjectError):
        env.resolve({0: 4, 1: 0, 2: 0, 3: 0})
    with pytest.raises(JointProjectError):
        env.resolve({0: -1, 1: 0, 2: 0, 3: 0})


def test_an_episode_is_exactly_eight_rounds_and_then_stops():
    env = JointProjectEnv()
    env.reset(seed=8)
    _drain_episode(env, lambda view: 0)
    assert env.done is True
    assert len(env.history) == 8
    with pytest.raises(JointProjectError):
        env.observe(0)
    with pytest.raises(JointProjectError):
        env.resolve({a: 0 for a in range(4)})


# ---------------------------------------------------------------------------
# Persistence, pledges and reputation
# ---------------------------------------------------------------------------


def test_cumulative_payoffs_persist_across_rounds_and_stay_private():
    env = JointProjectEnv()
    env.reset(seed=2)
    _drain_episode(env, lambda view: 3)
    manually_summed = 0.0
    for record in env.history:
        contributions = dict(record.contributions)
        manually_summed += float(env.config.bonus if record.success else 0) - env.true_types()[0] * contributions[0]
    assert env.total_payoffs()[0] == pytest.approx(manually_summed)
    # Every agent sees only its own cumulative payoff.
    env2 = JointProjectEnv()
    env2.reset(seed=2)
    env2.resolve({a: 1 for a in range(4)})
    view = env2.observe(1)
    assert isinstance(view.own_cumulative_payoff, float)
    assert not hasattr(view, "cumulative_payoffs")


def test_breaking_a_pledge_is_recorded_publicly():
    env = JointProjectEnv()
    env.reset(seed=4)
    env.resolve({0: 2, 1: 2, 2: 2, 3: 2})  # pledges
    env.resolve({0: 1, 1: 2, 2: 0, 3: 2})  # contributions
    record = env.history[0]
    assert record.pledge_broken == (0, 2)
    view = env.observe(0)
    assert dict(view.pledges_broken) == {0: 1, 1: 0, 2: 1, 3: 0}
    assert dict(view.pledges_kept) == {0: 0, 1: 1, 2: 0, 3: 1}


def test_a_pledge_of_zero_that_is_matched_counts_as_kept():
    env = JointProjectEnv()
    env.reset(seed=4)
    env.resolve({a: 0 for a in range(4)})
    env.resolve({a: 0 for a in range(4)})
    assert env.history[0].pledge_broken == ()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_the_same_seed_reproduces_the_types_and_the_trajectory():
    def play(seed):
        env = JointProjectEnv()
        env.reset(seed=seed)
        _drain_episode(env, lambda view: view.own_type % 4)
        return env.true_types(), env.total_payoffs()

    assert play(11) == play(11)
    assert play(11)[0] != play(12)[0] or play(11)[1] != play(12)[1]


def test_types_are_drawn_from_the_public_distribution():
    seen = set()
    for seed in range(50):
        env = JointProjectEnv()
        env.reset(seed=seed)
        seen.update(env.true_types())
    assert seen == {1, 2, 4}


# ---------------------------------------------------------------------------
# Information boundary
# ---------------------------------------------------------------------------


def test_an_agent_view_exposes_only_its_own_cost_type():
    env = JointProjectEnv()
    env.reset(seed=6)
    env.resolve({a: 1 for a in range(4)})
    true_types = env.true_types()
    for agent_id in range(4):
        view = env.observe(agent_id)
        jp.assert_information_safe(view)
        assert view.own_type == true_types[agent_id]
        for name in ("types", "other_types", "true_types", "full_information_optimum"):
            assert not hasattr(view, name)


def test_per_agent_payoffs_are_not_published_because_they_would_reveal_types():
    """The contract's key observability decision, pinned by a direct check.

    payoff_i = success*bonus - c_i*x_i.  With success and x_i public, publishing
    payoff_i would let anyone solve for c_i in one division, so the benchmark
    publishes only the aggregate surplus.
    """
    env = JointProjectEnv()
    env.reset(seed=9)
    types = env.true_types()
    env.resolve({a: 1 for a in range(4)})
    event = env.resolve({0: 2, 1: 1, 2: 0, 3: 3})
    assert "payoffs" not in event
    assert "total_surplus" in event
    record = env.history[0]
    assert not hasattr(record, "payoffs")
    # The aggregate surplus is consistent with the true types, and recovering
    # them needs the whole equation system rather than one division.
    contributions = [2, 1, 0, 3]
    expected_surplus = jp.round_joint_surplus(
        contributions=contributions, types=types, config=env.config
    )
    assert record.total_surplus == pytest.approx(expected_surplus)
    # No serialised public field names a type.
    dumped = json.dumps(
        {
            "pledges": record.pledges,
            "contributions": record.contributions,
            "success": record.success,
            "total_surplus": record.total_surplus,
            "broken": record.pledge_broken,
        }
    )
    assert "type" not in dumped.lower()


def test_aggregate_surplus_narrows_the_hidden_types_without_pinning_them_at_once():
    """The inference channel is real and it starts uncertain.

    Surviving type vectors are those consistent with the observed aggregate
    surpluses.  The true vector must always survive, the set must shrink after the
    first informative round, and it must never grow.
    """
    from itertools import product

    env = JointProjectEnv()
    env.reset(seed=15)
    types = env.true_types()
    candidates = [tuple(v) for v in product((1, 2, 4), repeat=4)]
    surviving = list(candidates)
    sizes = []
    round_no = 0
    while not env.done:
        # Vary contributions so the linear equations are independent.
        env.resolve(
            {
                a: (round_no + a) % (env.config.max_contribution + 1)
                for a in range(4)
            }
        )
        env.resolve(
            {
                a: (round_no + a + 1) % (env.config.max_contribution + 1)
                for a in range(4)
            }
        )
        round_no += 1
        record = env.history[-1]
        contributions = [dict(record.contributions)[a] for a in range(4)]
        surviving = [
            vector
            for vector in surviving
            if jp.round_joint_surplus(
                contributions=contributions, types=vector, config=env.config
            )
            == record.total_surplus
        ]
        sizes.append(len(surviving))

    assert tuple(types) in surviving, "the true type vector must remain consistent"
    assert sizes[0] < len(candidates), "the first round must carry information"
    assert all(later <= earlier for earlier, later in zip(sizes, sizes[1:])), (
        "evidence must never increase the candidate set"
    )
    assert sizes[-1] >= 1


def test_the_environment_module_never_hands_truth_to_a_view_constructor():
    """Static audit: AgentView is only ever constructed from the whitelist."""
    tree = ast.parse(inspect.getsource(jp))
    view_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AgentView"
    )
    field_names = {
        statement.target.id
        for statement in view_class.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }
    # Only the agent's own type is allowed to be type-bearing.
    assert "own_type" in field_names
    assert not {"types", "other_types", "true_types"} & field_names


def test_environment_truth_is_reachable_only_through_the_named_accessor():
    source = inspect.getsource(jp)
    # _types is assigned in reset and read by observe for the agent's own type,
    # by _resolve_round for payoffs, and by true_types for evaluation.
    assert "_types[agent_id]" in source
    assert "def true_types" in source
    env = JointProjectEnv()
    env.reset(seed=1)
    assert env.true_types() == env._types
