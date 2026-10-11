"""Tests for the SCK SecretMafia A/B harness.

These run without textarena: aggregation is exercised with synthetic episode
evaluations and ``run_ab`` is driven by a stub runner.  Live behaviour is covered
by tests/test_storybox_secret_mafia_live_v0.py.
"""
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
from narrative.longform.storybox_sck_v0 import BeliefState
from narrative.longform.storybox_textarena_secret_mafia_adapter_v0 import (
    mafia_world_id,
)

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


def test_action_regret_is_aggregated_per_action_kind():
    runtime = VariantRuntime(variant=PLAIN)
    runtime.episodes = [
        _episode("plain", seed=0, regret_kind="vote", regret=0.5),
        _episode("plain", seed=1, regret_kind="vote", regret=1.0),
        _episode("plain", seed=2, regret_kind="protect", regret=0.25),
    ]
    row = aggregate_variant(runtime)
    assert row["mean_action_regret_by_kind"]["vote"] == 0.75
    assert row["mean_action_regret_by_kind"]["protect"] == 0.25
    assert row["action_decisions_measured"] == 3


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
    assert set(report["variants"]) == {"plain", "belief"}

    # Every variant must be driven over the identical seed schedule.
    assert [call[2] for call in stub.calls[:3]] == [0, 1, 2]
    assert [call[2] for call in stub.calls[3:]] == [0, 1, 2]

    assert report["variants"]["plain"]["mean_brier_village_side"] is None
    assert report["variants"]["belief"]["mean_brier_village_side"] == 0.0
    assert report["variants"]["plain"]["information_leakage_count"] == 0

    assert set(UNAVAILABLE_METRICS).issubset(report["unavailable_metrics"])
    assert "vote_target_evidence" in report["unavailable_metrics"]
    assert (
        "mean_action_regret_by_kind.mafia_eliminate"
        in report["non_discriminating_metrics"]
    )


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
