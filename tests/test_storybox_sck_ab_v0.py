"""Tests for the SCK SecretMafia A/B harness.

These run without textarena: aggregation is exercised with synthetic episode
evaluations and ``run_ab`` is driven by a stub runner.  Live behaviour is covered
by tests/test_storybox_secret_mafia_live_v0.py.
"""
from narrative.longform import storybox_sck_ab_v0 as ab
from narrative.longform.storybox_sck_ab_v0 import (
    UNAVAILABLE_METRICS,
    VariantRuntime,
    aggregate_variant,
    run_ab,
    verify_shared_role_schedule,
)
from narrative.longform.storybox_sck_eval_v0 import (
    ActionCheckpoint,
    BeliefCheckpoint,
    EpisodeEvaluation,
    VariantConfig,
)
from narrative.longform.storybox_sck_v0 import BeliefState, SCKError
from narrative.longform.storybox_textarena_secret_mafia_adapter_v0 import (
    mafia_world_id,
)
from narrative.longform.storybox_textarena_secret_mafia_live_v0 import (
    BeliefPolicy,
    build_policy,
)

import pytest

PLAIN = VariantConfig("plain", False, False, 0, False)
BELIEF = VariantConfig("belief", True, True, 0, True)

ROLES_6 = {0: "Villager", 1: "Mafia", 2: "Villager", 3: "Detective", 4: "Mafia", 5: "Doctor"}


def _episode(
    variant_id: str,
    *,
    seed: int,
    true_mafia=(1, 4),
    village_won: bool = True,
    steps: int = 40,
    regret_kind: str = "vote",
    regret: float = 0.5,
    with_belief: bool = False,
) -> EpisodeEvaluation:
    rewards = {
        pid: (1 if (role != "Mafia") == village_won else -1)
        for pid, role in ROLES_6.items()
    }
    evaluation = EpisodeEvaluation(
        variant_id=variant_id,
        won=rewards[0] == 1,
        utility=float(rewards[0]),
    )
    role_wins: dict[str, dict[str, int]] = {}
    for pid, role in ROLES_6.items():
        row = role_wins.setdefault(role, {"played": 0, "won": 0})
        row["played"] += 1
        if rewards[pid] == 1:
            row["won"] += 1
    evaluation.metadata.update(
        {
            "seed": seed,
            "num_players": 6,
            "mafia_count": 2,
            "steps": steps,
            "invalid_moves": 0,
            "true_mafia": list(true_mafia),
            "actor_results": [
                {
                    "actor_id": pid,
                    "role": role,
                    "reward": rewards[pid],
                    "won": rewards[pid] == 1,
                    "decisions": 1,
                }
                for pid, role in ROLES_6.items()
            ],
            "role_wins": role_wins,
            "decision_count": 6,
        }
    )
    evaluation.action_checkpoints.append(
        ActionCheckpoint(
            step_id=f"s{seed}",
            chosen_action_id=f"{regret_kind}:1",
            action_values={f"{regret_kind}:1": 1.0, f"{regret_kind}:2": 0.0},
            chosen_value=1.0 - regret,
        )
    )
    if with_belief:
        evaluation.belief_checkpoints.append(
            BeliefCheckpoint(
                step_id=f"b{seed}",
                belief=BeliefState({mafia_world_id(sorted(true_mafia)): 1.0}),
                true_hypothesis=mafia_world_id(sorted(true_mafia)),
            )
        )
    return evaluation


def test_village_and_mafia_faction_win_rates_are_complementary():
    runtime = VariantRuntime(variant=PLAIN)
    runtime.episodes = [
        _episode("plain", seed=0, village_won=True),
        _episode("plain", seed=1, village_won=False),
        _episode("plain", seed=2, village_won=True),
        _episode("plain", seed=3, village_won=True),
    ]
    row = aggregate_variant(runtime)
    assert row["village_faction_win_rate"] == 0.75
    assert row["mafia_faction_win_rate"] == 0.25
    assert row["episodes"] == 4


def test_per_role_table_accumulates_seats_across_episodes():
    runtime = VariantRuntime(variant=PLAIN)
    runtime.episodes = [
        _episode("plain", seed=0, village_won=True),
        _episode("plain", seed=1, village_won=True),
    ]
    row = aggregate_variant(runtime)["per_role"]
    assert row["Mafia"]["played"] == 4
    assert row["Mafia"]["won"] == 0
    assert row["Villager"]["played"] == 4
    assert row["Villager"]["won"] == 4
    assert row["Detective"]["win_rate"] == 1.0


def test_missing_belief_reports_brier_as_unavailable_not_zero():
    runtime = VariantRuntime(variant=PLAIN)
    runtime.episodes = [_episode("plain", seed=0), _episode("plain", seed=1)]
    row = aggregate_variant(runtime)
    assert row["mean_brier_village_side"] is None
    assert row["brier_episodes_measured"] == 0

    belief_runtime = VariantRuntime(variant=BELIEF)
    belief_runtime.episodes = [
        _episode("belief", seed=0, with_belief=True),
        _episode("belief", seed=1, with_belief=True),
    ]
    belief_row = aggregate_variant(belief_runtime)
    assert belief_row["mean_brier_village_side"] == 0.0
    assert belief_row["brier_episodes_measured"] == 2


def test_immediate_target_loss_is_aggregated_per_action_kind_as_a_diagnostic():
    runtime = VariantRuntime(variant=PLAIN)
    runtime.episodes = [
        _episode("plain", seed=0, regret_kind="vote", regret=0.5),
        _episode("plain", seed=1, regret_kind="vote", regret=1.0),
        _episode("plain", seed=2, regret_kind="protect", regret=0.25),
    ]
    row = aggregate_variant(runtime)
    by_kind = row["immediate_target_loss_by_kind_diagnostic"]
    assert by_kind["vote"] == 0.75
    assert by_kind["protect"] == 0.25
    assert row["mean_immediate_target_loss_diagnostic"] == pytest.approx(0.5833333333333334)
    assert row["action_decisions_measured"] == 3
    # The old name must be gone so no artifact implies true sequential regret.
    assert "mean_action_regret" not in row
    assert "mean_action_regret_by_kind" not in row


def test_shared_role_schedule_check_passes_and_detects_mismatch():
    good_a, good_b = VariantRuntime(variant=PLAIN), VariantRuntime(variant=BELIEF)
    good_a.episodes = [_episode("plain", seed=0, true_mafia=(1, 4))]
    good_b.episodes = [_episode("belief", seed=0, true_mafia=(1, 4))]
    assert verify_shared_role_schedule([good_a, good_b])["verified"] is True

    bad_b = VariantRuntime(variant=BELIEF)
    bad_b.episodes = [_episode("belief", seed=0, true_mafia=(2, 5))]
    check = verify_shared_role_schedule([good_a, bad_b])
    assert check["verified"] is False
    assert check["mismatches"] == [
        {
            "seed": 0,
            "variant": "belief",
            "mafia": [2, 5],
            "reference_variant": "plain",
            "reference_mafia": [1, 4],
        }
    ]


class _StubRunner:
    """Deterministic stand-in for the live runner."""

    def __init__(self):
        self.calls = []

    def run_episode(self, *, variant, num_players, seed):
        self.calls.append((variant.variant_id, num_players, seed))
        return _episode(
            variant.variant_id,
            seed=seed,
            village_won=(seed % 2 == 0),
            with_belief=variant.belief_enabled,
        )


def test_run_ab_reports_design_validity_and_unavailable_metrics():
    stub = _StubRunner()
    report = run_ab(
        variants=[PLAIN, BELIEF],
        episodes_per_variant=3,
        num_players=6,
        runner=stub,
    )

    assert report["design"]["same_seed_schedule_for_all_variants"] is True
    assert report["design"]["role_schedule_check"]["verified"] is True
    assert report["design"]["seeds"] == [0, 1, 2]
    assert report["design"]["informed_policy_tie_break"] == "lowest_id"
    assert report["design"]["target_action_format"] == "native"
    assert set(report["variants"]) == {"plain", "belief"}

    # Every variant must be driven over the identical seed schedule.
    assert [call[2] for call in stub.calls[:3]] == [0, 1, 2]
    assert [call[2] for call in stub.calls[3:]] == [0, 1, 2]

    assert report["variants"]["plain"]["mean_brier_village_side"] is None
    assert report["variants"]["belief"]["mean_brier_village_side"] == 0.0
    assert report["variants"]["plain"]["information_leakage_count"] == 0

    assert set(UNAVAILABLE_METRICS).issubset(report["unavailable_metrics"])
    assert (
        "immediate_target_loss_by_kind_diagnostic.mafia_eliminate"
        in report["non_discriminating_metrics"]
    )
    # Peer 0016 Q5: the metric is a diagnostic, and the artifact says so.
    assert "action_regret_renamed" in report["metric_notes"]
    assert "immediate target loss" in " ".join(
        report["primary_metrics"]["secondary_diagnostics"]
    )
    assert (
        report["variants"]["plain"]["mean_immediate_target_loss_diagnostic"]
        is not None
    )
    assert "mean_action_regret" not in report["variants"]["plain"]


def test_run_ab_retains_one_replay_record_per_episode():
    report = run_ab(
        variants=[PLAIN, BELIEF],
        episodes_per_variant=3,
        runner=_StubRunner(),
    )
    records = report["episode_records"]
    assert len(records) == 6
    assert {row["variant"] for row in records} == {"plain", "belief"}
    assert sorted(row["seed"] for row in records if row["variant"] == "plain") == [0, 1, 2]
    for row in records:
        assert row["true_mafia"] == [1, 4]
        assert row["mean_immediate_target_loss_diagnostic"] is not None
        assert row["steps"] == 40
        assert row["information_leakage_count"] == 0
    assert "failure_replay_retention" in report


def test_informed_policies_break_ties_by_lowest_id_unless_asked_otherwise():
    policy = BeliefPolicy(num_players=6, seed=1)
    assert policy.tie_break == "lowest_id"
    assert policy._argmax([3, 1, 2], lambda t: 1.0) == 1
    assert policy._argmin([3, 1, 2], lambda t: 0.0) == 1
    # Near-equal values still count as a tie.
    assert policy._argmax([3, 1], lambda t: 1.0 + (1e-15 if t == 3 else 0.0)) == 1

    stochastic = BeliefPolicy(num_players=6, seed=1, tie_break="random")
    picks = {stochastic._argmax([1, 2, 3, 4, 5], lambda t: 0.0) for _ in range(30)}
    assert len(picks) > 1


def test_unknown_tie_break_mode_is_rejected():
    with pytest.raises(SCKError):
        BeliefPolicy(num_players=6, seed=1, tie_break="coin-flip")


def test_policy_classes_override_is_honoured_and_validated():
    class Custom(BeliefPolicy):
        pass

    built = build_policy(
        BELIEF, num_players=6, seed=0, policy_classes={"belief": Custom}
    )
    assert isinstance(built, Custom)

    with pytest.raises(SCKError):
        build_policy(
            PLAIN, num_players=6, seed=0, policy_classes={"belief": Custom}
        )


def test_discrimination_report_shape(monkeypatch):
    """The diagnostic must be driven by the runner's documented override."""
    captured = {}

    class _FakeRunner:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.episodes = 0

        def run_episode(self, *, variant, num_players, seed):
            self.episodes += 1
            return _episode("belief", seed=seed, with_belief=True)

    monkeypatch.setattr(ab, "SecretMafiaLiveRunner", _FakeRunner)
    report = ab.discrimination_report(episodes=2)

    assert report["episodes"] == 2
    assert report["overall"]["decisions"] == 0
    assert report["overall"]["flat_fraction"] is None
    assert isinstance(report["by_role"], dict)
    assert "flat_fraction" in report["interpretation"]
    # The probe must be injected through policy_classes, not by editing policies.
    assert "policy_classes" in captured
    assert set(captured["policy_classes"]) == {"belief"}


def test_cross_play_conditions_assign_arms_by_role():
    plans = ab.cross_play_conditions("belief_planning")
    assert set(plans) == {
        "all_baseline",
        "belief_planning_village",
        "belief_planning_mafia",
        "all_belief_planning",
    }
    assert set(plans["all_baseline"].values()) == {"plain"}
    assert plans["belief_planning_village"]["Mafia"] == "plain"
    assert plans["belief_planning_village"]["Villager"] == "belief_planning"
    assert plans["belief_planning_village"]["Doctor"] == "belief_planning"
    assert plans["belief_planning_village"]["Detective"] == "belief_planning"
    assert plans["belief_planning_mafia"]["Mafia"] == "belief_planning"
    assert plans["belief_planning_mafia"]["Villager"] == "plain"
    assert set(plans["all_belief_planning"].values()) == {"belief_planning"}


def test_seat_variants_for_condition_maps_roles_to_seats():
    plan = ab.cross_play_conditions("belief")["belief_village"]
    schedule = {0: "Mafia", 1: "Villager", 2: "Detective", 3: "Mafia", 4: "Villager", 5: "Doctor"}
    seat_variants = ab.seat_variants_for_condition(plan, schedule)
    assert seat_variants[0].variant_id == "plain"
    assert seat_variants[3].variant_id == "plain"
    assert seat_variants[1].variant_id == "belief"
    assert seat_variants[2].variant_id == "belief"
    assert seat_variants[5].variant_id == "belief"

    with pytest.raises(ValueError):
        ab.seat_variants_for_condition(plan, {0: "Alien"})


def _cross_play_episode(condition_id, seed, seat_policy, village_won):
    # Use the same role table the synthetic episode reports, so the seat plan and
    # actor_results cannot disagree.
    evaluation = _episode(
        condition_id, seed=seed, true_mafia=(1, 4), village_won=village_won
    )
    evaluation.metadata["condition_id"] = condition_id
    evaluation.metadata["seat_policy_by_actor"] = {
        str(pid): seat_policy[role] for pid, role in ROLES_6.items()
    }
    evaluation.metadata["invalid_moves"] = 0
    return evaluation


def test_cross_play_informed_faction_rate_only_defined_for_one_sided_conditions():
    plan = ab.cross_play_conditions("belief")["belief_village"]
    episodes = [
        _cross_play_episode("belief_village", 0, plan, village_won=True),
        _cross_play_episode("belief_village", 1, plan, village_won=False),
    ]
    row = ab.aggregate_cross_play(episodes)
    assert row["village_faction_win_rate"] == 0.5
    assert row["informed_faction"] == "Village"
    assert row["informed_faction_win_rate"] == 0.5
    assert row["informed_faction_episodes"] == 2

    # Mafia-informed condition: the informed faction is Mafia.
    mafia_plan = ab.cross_play_conditions("belief")["belief_mafia"]
    mafia_row = ab.aggregate_cross_play(
        [_cross_play_episode("belief_mafia", 0, mafia_plan, village_won=False)]
    )
    assert mafia_row["informed_faction"] == "Mafia"
    assert mafia_row["informed_faction_win_rate"] == 1.0

    # Both factions informed, so no single informed side exists.
    all_plan = ab.cross_play_conditions("belief")["all_belief"]
    all_row = ab.aggregate_cross_play(
        [_cross_play_episode("all_belief", 0, all_plan, village_won=True)]
    )
    assert all_row["informed_faction_win_rate"] is None
    assert all_row["informed_faction_episodes"] == 0


class _CrossPlayStubRunner:
    """Stub runner that records the seat plan it was handed."""

    mafia_ratio = 0.25
    tie_break = "lowest_id"

    def __init__(self):
        self.calls = []

    def run_episode(self, *, variant=None, seat_variants=None, condition_id=None,
                    num_players=6, seed=0):
        self.calls.append((condition_id, seat_variants, seed))
        label = condition_id or variant.variant_id
        if seat_variants is None:
            seat_policy = {role: variant.variant_id for role in ab._ROLE_ARMS}
        else:
            seat_policy = {
                ab._ROLE_ARMS[pid % len(ab._ROLE_ARMS)]: seat_variants[pid].variant_id
                for pid in range(num_players)
            }
        return _cross_play_episode(label, seed, seat_policy, village_won=(seed % 2 == 0))


def _fixed_role_schedule(*, num_players, seed, mafia_ratio=0.25, discussion_rounds=3):
    # Must agree with ROLES_6, which the synthetic episodes report.
    base = ["Villager", "Mafia", "Villager", "Detective", "Mafia", "Doctor"]
    return {pid: base[pid % len(base)] for pid in range(num_players)}


def test_run_cross_play_uses_one_shared_seed_schedule_for_every_condition():
    stub = _CrossPlayStubRunner()
    report = ab.run_cross_play(
        informed_variant_ids=("belief",),
        episodes_per_condition=3,
        runner=stub,
        role_schedule_fn=_fixed_role_schedule,
    )

    assert set(report["conditions"]) == {
        "all_baseline",
        "belief_village",
        "belief_mafia",
        "all_belief",
    }
    # Four conditions, three seeds each, reference first.
    assert len(stub.calls) == 12
    assert stub.calls[0][0] == "all_baseline"
    assert stub.calls[0][1] is None
    for condition_id, seat_variants, seed in stub.calls:
        assert seed in (0, 1, 2)
        if condition_id != "all_baseline":
            assert seat_variants is not None
            assert set(seat_variants) == set(range(6))

    assert report["design"]["same_seed_schedule_for_every_condition"] is True
    assert report["design"]["role_schedule_check"]["verified"] is True
    assert report["design"]["role_schedule_check"]["episodes_checked"] == 12
    assert report["evidence_class"].startswith("primary strength evidence")
    assert set(report["cross_play_effect"]) == {"belief"}
    effect = report["cross_play_effect"]["belief"]
    assert set(effect) >= {
        "informed_village_vs_baseline_mafia",
        "informed_mafia_vs_baseline_village",
        "all_informed_self_play",
    }
    assert effect["informed_village_vs_baseline_mafia"]["village_delta"] is not None


def test_run_cross_play_detects_a_role_schedule_mismatch():
    class _LyingRunner(_CrossPlayStubRunner):
        def run_episode(self, *, variant=None, seat_variants=None, condition_id=None,
                        num_players=6, seed=0):
            evaluation = super().run_episode(
                variant=variant,
                seat_variants=seat_variants,
                condition_id=condition_id,
                num_players=num_players,
                seed=seed,
            )
            if condition_id == "belief_village":
                evaluation.metadata["true_mafia"] = [5]
            return evaluation

    report = ab.run_cross_play(
        informed_variant_ids=("belief",),
        episodes_per_condition=2,
        runner=_LyingRunner(),
        role_schedule_fn=_fixed_role_schedule,
    )
    check = report["design"]["role_schedule_check"]
    assert check["verified"] is False
    assert check["mismatches"]
    assert check["mismatches"][0]["condition"] == "belief_village"


def _voting_episode(condition_id, seed, votes, true_mafia=(1, 4)):
    """Synthetic episode whose day-vote decisions are exactly ``votes``."""
    evaluation = _episode(condition_id, seed=seed, true_mafia=true_mafia)
    evaluation.action_checkpoints = []
    for step, (actor, target) in enumerate(votes):
        evaluation.action_checkpoints.append(
            ActionCheckpoint(
                step_id=f"p{actor}-n1-Day-Voting-{step + 1}",
                chosen_action_id=f"vote:{target}",
                action_values={f"vote:{target}": 0.0},
                chosen_value=0.0,
            )
        )
    return evaluation


def test_vote_coordination_detects_a_unanimous_mafia_bloc_that_controls_the_vote():
    # Mafia seats 1 and 4 both name player 2; the four village seats scatter.
    episode = _voting_episode(
        "belief_mafia",
        seed=0,
        votes=[(1, 2), (4, 2), (0, 3), (2, 3), (3, 5), (5, 2)],
    )
    report = ab.vote_coordination_report([episode])
    assert report["day_vote_rounds_with_two_mafia_votes"] == 1
    assert report["mafia_unanimous_rate"] == 1.0
    # votes: 2 -> 3, 3 -> 2, 5 -> 1, so the Mafia's target is the plurality.
    assert report["mafia_target_is_plurality_rate"] == 1.0
    assert report["mean_distinct_mafia_targets"] == 1.0
    # Village votes are 0->3, 2->3, 3->5, 5->2, i.e. three distinct targets.
    assert report["mean_distinct_village_targets"] == 3.0


def test_vote_coordination_reports_a_split_mafia_vote_and_lost_plurality():
    # Mafia seats disagree, and their shared-target test cannot apply.
    split = _voting_episode(
        "all_baseline", seed=0, votes=[(1, 2), (4, 3), (0, 5), (2, 5), (3, 5), (5, 5)]
    )
    report = ab.vote_coordination_report([split])
    assert report["mafia_unanimous_rate"] == 0.0
    assert report["mafia_target_is_plurality_rate"] is None
    assert report["mean_distinct_mafia_targets"] == 2.0


def test_vote_coordination_ignores_night_phases_and_rounds_with_one_mafia_vote():
    evaluation = _episode("all_baseline", seed=0, true_mafia=(1, 4))
    evaluation.action_checkpoints = [
        ActionCheckpoint(
            step_id="p1-n1-Night-Mafia-1",
            chosen_action_id="mafia_eliminate:0",
            action_values={"mafia_eliminate:0": 1.0},
            chosen_value=1.0,
        ),
        ActionCheckpoint(
            step_id="p1-n1-Day-Voting-1",
            chosen_action_id="vote:2",
            action_values={"vote:2": 1.0},
            chosen_value=1.0,
        ),
    ]
    report = ab.vote_coordination_report([evaluation])
    # Only one Mafia seat voted on the day, so no bloc test is possible.
    assert report["day_vote_rounds_with_two_mafia_votes"] == 0
    assert report["mafia_unanimous_rate"] is None


def test_run_cross_play_reports_coordination_per_condition():
    report = ab.run_cross_play(
        informed_variant_ids=("belief",),
        episodes_per_condition=2,
        runner=_CrossPlayStubRunner(),
        role_schedule_fn=_fixed_role_schedule,
    )
    for row in report["conditions"].values():
        assert "vote_coordination" in row
        assert "mafia_unanimous_rate" in row["vote_coordination"]


def test_run_ab_marks_role_schedule_mismatch_in_the_report():
    class _InconsistentRunner(_StubRunner):
        def run_episode(self, *, variant, num_players, seed):
            evaluation = super().run_episode(
                variant=variant, num_players=num_players, seed=seed
            )
            if variant.variant_id == "belief":
                evaluation.metadata["true_mafia"] = [0, 2]
            return evaluation

    report = run_ab(
        variants=[PLAIN, BELIEF],
        episodes_per_variant=2,
        runner=_InconsistentRunner(),
    )
    assert report["design"]["role_schedule_check"]["verified"] is False
