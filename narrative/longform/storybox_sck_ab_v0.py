"""Shared-seed A/B harness for the StoryBox Strategic Cognition Kernel.

Runs the live TextArena SecretMafia runner across the four variants declared in
``runtime/adaptation/storybox/sck-secret-mafia-ab-v0.json`` on an identical seed
schedule and reports the metrics that plan asks for.

Metric policy
-------------
The task's quality standard puts calibration, evidence updating, action regret
and information leakage *before* win rate, and an all-seats-self-play win rate is
a zero-sum bookkeeping number rather than a quality measure.  This harness
therefore leads with:

* ``mean_immediate_target_loss_diagnostic`` -- per-decision quality against a
  truth oracle (``+1`` faction-optimal, ``-1`` faction-worst target).  Diagnostic
  only, per peer decision 0016 Q5: it can improve while terminal play gets
  worse, so it is never the acceptance metric;
* ``mean_brier`` -- belief calibration, village-side only.  A Mafia actor's
  belief is a point mass on its own team by construction, so including it would
  report a meaningless perfect score;
* ``information_leakage_count`` -- safety.

Win rates are still reported, explicitly labelled as descriptive self-play
outcomes, because the plan lists them.

Metrics that cannot be computed are reported as ``null`` with a reason in
``unavailable_metrics``; they are never estimated.

Validity
--------
The plan's minimum validity condition ("all variants receive identical
public/private observations for the same seed and role schedule") cannot hold
literally once policies choose different actions, because the trajectories then
diverge.  What *is* enforced and verified here is that every variant receives the
identical initial role schedule for the same seed, and that the environment,
player count, discussion rounds and observation pipeline are identical.  The
harness verifies the role-schedule part rather than asserting it.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from .storybox_sck_eval_v0 import DEFAULT_AB_VARIANTS, EpisodeEvaluation, VariantConfig
from .storybox_textarena_secret_mafia_live_v0 import (
    DEFAULT_TARGET_ACTION_FORMAT,
    TARGET_ACTION_FORMATS,
    BeliefPolicy,
    SecretMafiaLiveRunner,
    load_textarena_secret_mafia_env,
    secret_mafia_role_schedule,
)
from .storybox_textarena_secret_mafia_adapter_v0 import (
    marginal_mafia_probabilities,
)

UNAVAILABLE_METRICS = {
    "persuasion_delta": (
        "Discussion uses a deterministic template renderer with no LLM listener, "
        "so no persuasive effect can be measured."
    ),
    "strategy_diversity": (
        "Requires an embedding or paraphrase model; not implemented in v0."
    ),
    "runtime_and_token_cost": (
        "No model calls are made in this run, so token cost is not applicable. "
        "Wall-clock runtime is recorded in execution.wall_clock_seconds."
    ),
    "strict_identical_observations": (
        "Once variants choose different actions their trajectories diverge, so "
        "identical observations across variants cannot hold beyond the first "
        "divergence. Initial role schedules are shared and verified instead."
    ),
    "vote_target_evidence": (
        "RESOLVED: no longer unavailable. Target actions are submitted as '[N]', "
        "which survives State.add_observation's role-tag stripping, so day-vote "
        "targets reach later actors through the ordinary observation stream. This "
        "entry is retained only to record that the earlier limitation was lifted "
        "by peer decision 0016 Q1; see target_action_format in the design block."
    ),
    "replay_calibrated_evidence_model": (
        "Not implemented yet. Peer decision 0016 Q4 requires a symmetric evidence "
        "feature set fitted on a training seed partition and frozen before "
        "held-out evaluation. The current hand-specified BehaviorEvidenceModel is "
        "still what the belief variants use."
    ),
}


@dataclass
class VariantRuntime:
    variant: VariantConfig
    episodes: list[EpisodeEvaluation] = field(default_factory=list)
    wall_clock_seconds: float = 0.0


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _episode_all_seat_rewards(evaluation: EpisodeEvaluation) -> list[float]:
    return [
        float(row["reward"])
        for row in evaluation.metadata.get("actor_results", [])
        if row.get("reward") is not None
    ]


def aggregate_variant(runtime: VariantRuntime) -> dict[str, Any]:
    episodes = runtime.episodes
    if not episodes:
        raise ValueError("cannot aggregate a variant with no episodes")

    reports = [episode.summary() for episode in episodes]
    focal_wins = [1.0 if row["won"] else 0.0 for row in reports if row["won"] is not None]
    focal_utilities = [float(row["utility"]) for row in reports if row["utility"] is not None]
    all_seat_utilities = [
        value for evaluation in episodes for value in _episode_all_seat_rewards(evaluation)
    ]

    # Brier is village-side only, so a None value means genuinely unavailable for
    # that episode (plain and memory carry no belief at all).
    brier_values = [
        float(row["mean_brier"])
        for row in reports
        if row["mean_brier"] is not None
    ]

    regret_by_kind: dict[str, list[float]] = {}
    for evaluation in episodes:
        for checkpoint in evaluation.action_checkpoints:
            kind = str(checkpoint.chosen_action_id).split(":")[0]
            regret_by_kind.setdefault(kind, []).append(checkpoint.regret)
    regret_means = {
        kind: _mean(values) for kind, values in sorted(regret_by_kind.items())
    }
    all_regrets = [value for values in regret_by_kind.values() for value in values]

    role_table: dict[str, dict[str, Any]] = {}
    for evaluation in episodes:
        for role, row in evaluation.metadata.get("role_wins", {}).items():
            entry = role_table.setdefault(role, {"played": 0, "won": 0})
            entry["played"] += int(row["played"])
            entry["won"] += int(row["won"])
    for entry in role_table.values():
        entry["win_rate"] = entry["won"] / entry["played"] if entry["played"] else None

    steps = [int(evaluation.metadata["steps"]) for evaluation in episodes]
    village_episode_wins = []
    for evaluation in episodes:
        rows = evaluation.metadata.get("actor_results", [])
        village_seats = [row for row in rows if row["role"] != "Mafia"]
        if village_seats:
            village_episode_wins.append(
                1.0 if all(row["won"] for row in village_seats) else 0.0
            )
    village_faction_win_rate = _mean(village_episode_wins)
    return {
        "variant_id": runtime.variant.variant_id,
        "episodes": len(episodes),
        "village_faction_win_rate": village_faction_win_rate,
        "mafia_faction_win_rate": (
            None
            if village_faction_win_rate is None
            else 1.0 - village_faction_win_rate
        ),
        "self_play_win_rate_focal_seat_mixed_roles": _mean(focal_wins),
        "self_play_mean_utility_focal_seat": _mean(focal_utilities),
        "self_play_mean_utility_all_seats": _mean(all_seat_utilities),
        "mean_brier_village_side": _mean(brier_values),
        "brier_episodes_measured": len(brier_values),
        # Diagnostic only, per peer decision 0016 Q5: this scores immediate
        # target correctness against a truth oracle and ignores downstream
        # coordination, information value, tie mechanics and future responses.
        # It can improve while terminal play gets worse, so it must never be
        # read as a quality verdict on its own.
        "mean_immediate_target_loss_diagnostic": _mean(all_regrets),
        "immediate_target_loss_by_kind_diagnostic": regret_means,
        "action_decisions_measured": len(all_regrets),
        "information_leakage_count": sum(
            int(row["information_leakage_count"]) for row in reports
        ),
        "claim_contradiction_count": sum(
            int(row["claim_contradiction_count"]) for row in reports
        ),
        "per_role": role_table,
        "mean_steps": _mean([float(x) for x in steps]),
        "wall_clock_seconds": runtime.wall_clock_seconds,
        "invalid_moves": sum(int(e.metadata["invalid_moves"]) for e in episodes),
    }


def verify_shared_role_schedule(runtimes: Iterable[VariantRuntime]) -> dict[str, Any]:
    """Confirm every variant saw the same Mafia assignment for the same seed."""
    schedules: dict[str, dict[int, list[int]]] = {}
    for runtime in runtimes:
        for evaluation in runtime.episodes:
            seed = int(evaluation.metadata["seed"])
            schedules.setdefault(runtime.variant.variant_id, {})[seed] = list(
                evaluation.metadata["true_mafia"]
            )
    reference_id = next(iter(schedules))
    reference = schedules[reference_id]
    mismatches = []
    for variant_id, schedule in schedules.items():
        for seed, mafia in schedule.items():
            if seed in reference and reference[seed] != mafia:
                mismatches.append(
                    {
                        "seed": seed,
                        "variant": variant_id,
                        "mafia": mafia,
                        "reference_variant": reference_id,
                        "reference_mafia": reference[seed],
                    }
                )
    return {
        "verified": not mismatches,
        "reference_variant": reference_id,
        "seeds_per_variant": {k: len(v) for k, v in schedules.items()},
        "mismatches": mismatches,
    }


def episode_record(evaluation: EpisodeEvaluation) -> dict[str, Any]:
    """Compact per-episode record kept as failure replay retention.

    The second milestone requires failure replay retention.  No model calls,
    prompts or per-step transcripts exist in v0, so the retained replay is the
    episode's seed, role schedule, outcome and score.
    """
    checkpoints = evaluation.action_checkpoints
    mean_regret = (
        sum(checkpoint.regret for checkpoint in checkpoints) / len(checkpoints)
        if checkpoints
        else None
    )
    summary = evaluation.summary()
    return {
        "variant": evaluation.variant_id,
        "seed": evaluation.metadata.get("seed"),
        "true_mafia": evaluation.metadata.get("true_mafia"),
        "village_won": evaluation.metadata.get("village_won"),
        "steps": evaluation.metadata.get("steps"),
        "nights_played": evaluation.metadata.get("nights_played"),
        "invalid_moves": evaluation.metadata.get("invalid_moves"),
        "termination_reason": evaluation.metadata.get("termination_reason"),
        "decision_count": evaluation.metadata.get("decision_count"),
        "mean_immediate_target_loss_diagnostic": mean_regret,
        "mean_brier_village_side": summary["mean_brier"],
        "information_leakage_count": summary["information_leakage_count"],
    }


def run_ab(
    *,
    variants: Sequence[VariantConfig] | None = None,
    episodes_per_variant: int = 50,
    num_players: int = 6,
    seed_start: int = 0,
    discussion_rounds: int = 3,
    tie_break: str = "lowest_id",
    action_format: str = DEFAULT_TARGET_ACTION_FORMAT,
    public_vote_record: bool = False,
    runner: SecretMafiaLiveRunner | None = None,
    progress: bool = False,
) -> dict[str, Any]:
    variants = tuple(variants or DEFAULT_AB_VARIANTS)
    runner = runner or SecretMafiaLiveRunner(
        discussion_rounds=discussion_rounds,
        tie_break=tie_break,
        action_format=action_format,
        public_vote_record=public_vote_record,
    )
    seeds = list(range(seed_start, seed_start + episodes_per_variant))
    runtimes: list[VariantRuntime] = []

    for variant in variants:
        runtime = VariantRuntime(variant=variant)
        started = time.perf_counter()
        for index, seed in enumerate(seeds):
            runtime.episodes.append(
                runner.run_episode(
                    variant=variant, num_players=num_players, seed=seed
                )
            )
            if progress and (index + 1) % 50 == 0:
                print(
                    f"  {variant.variant_id}: {index + 1}/{len(seeds)} episodes",
                    flush=True,
                )
        runtime.wall_clock_seconds = time.perf_counter() - started
        runtimes.append(runtime)
        if progress:
            print(
                f"  {variant.variant_id}: done in {runtime.wall_clock_seconds:.1f}s",
                flush=True,
            )

    role_check = verify_shared_role_schedule(runtimes)
    variant_reports = {
        runtime.variant.variant_id: aggregate_variant(runtime) for runtime in runtimes
    }
    episode_records = [
        episode_record(evaluation)
        for runtime in runtimes
        for evaluation in runtime.episodes
    ]
    return {
        "schema_version": 1,
        "status": (
            "first_milestone_smoke_test_run"
            if episodes_per_variant <= 50
            else "second_milestone_run"
        ),
        "historical_world_writeback": False,
        "environment": {
            "primary": "TextArena SecretMafia",
            "textarena_version": _textarena_version(),
            "player_counts": [num_players],
            "discussion_rounds": discussion_rounds,
            "player_counts_planned_not_run": [8, 10],
        },
        "design": {
            "episodes_per_variant": episodes_per_variant,
            "seeds": seeds,
            "same_seed_schedule_for_all_variants": True,
            "num_players": num_players,
            "all_seats_driven_by_one_policy": True,
            "informed_policy_tie_break": tie_break,
            "target_action_format": action_format,
            "reconstructed_public_vote_record": public_vote_record,
            "role_schedule_check": role_check,
        },
        "variants": variant_reports,
        "episode_records": episode_records,
        "failure_replay_retention": (
            "episode_records holds one compact record per episode (seed, role "
            "schedule, outcome, steps, regret, calibration, leakage)."
        ),
        "primary_metrics": {
            "source": "peer decision 2026-10-11-0016-peer-decision-sck-methodology-next-gate Q5",
            "primary": [
                "paired cross-play terminal utility / faction win rate against fixed opponents",
                "belief calibration and Brier/log loss on held-out episodes",
                "belief-discrimination flat fraction / entropy change after informative evidence",
                "information leakage",
                "cross-play exploitability / asymmetry diagnostics",
            ],
            "secondary_diagnostics": [
                "immediate target loss (formerly called action regret)",
                "vote concentration / coordination",
                "target-distribution collapse or predictability",
            ],
            "note": "This all-seats self-play report can only supply the mechanism metrics. Paired cross-play is a separate harness and is the primary strength evidence.",
        },
        "metric_notes": {
            "action_regret_renamed": (
                "mean_action_regret and mean_action_regret_by_kind were renamed to "
                "mean_immediate_target_loss_diagnostic and "
                "immediate_target_loss_by_kind_diagnostic per peer decision 0016 Q5, "
                "because the name implied true sequential regret. Historic artifacts "
                "under runtime/adaptation/storybox/ still use the old key names and "
                "are retained unchanged as historical diagnostics."
            ),
        },
        "unavailable_metrics": UNAVAILABLE_METRICS,
        "non_discriminating_metrics": {
            "immediate_target_loss_by_kind_diagnostic.mafia_eliminate": (
                "Structurally zero for every variant: the Mafia's legal night "
                "targets already exclude its own team, so the truth oracle scores "
                "every legal choice faction-optimal. This metric cannot separate "
                "variants in SecretMafia and is reported only for completeness."
            )
        },
        "reading_notes": [
            "Every seat is driven by the same policy, so win rates are self-play outcomes and are zero-sum across factions; they are descriptive, not the quality claim.",
            "The quality claim rests on calibration, correct evidence updating, action regret and leakage, in that order, as the task's quality standard requires.",
            "mean_brier_village_side is null for plain and memory because those variants keep no belief at all; it is unavailable, not zero.",
            "self_play_win_rate_focal_seat_mixed_roles follows seat 0, whose role varies by seed, so it mixes factions. Read village_faction_win_rate and per_role instead.",
        ],
    }


def discrimination_report(
    *,
    episodes: int = 50,
    num_players: int = 6,
    seed_start: int = 0,
    discussion_rounds: int = 3,
    action_format: str = DEFAULT_TARGET_ACTION_FORMAT,
    public_vote_record: bool = False,
) -> dict[str, Any]:
    """Measure whether the belief actually separates the legal targets.

    A belief state is only useful if its marginal Mafia probabilities differ
    across the targets the actor may choose.  When every legal target has the
    same marginal, the informed policy's choice is decided entirely by its
    tie-break, not by inference.  This diagnostic reports how often that happens,
    per role and per phase, so the A/B numbers can be interpreted honestly.

    It instruments the ``belief`` policy through the runner's documented
    ``policy_classes`` override; it changes no policy rule.
    """
    samples: list[dict[str, Any]] = []

    class _Probe(BeliefPolicy):
        def choose_target(self, view):
            target = super().choose_target(view)
            belief = self.beliefs.get(view.actor_id)
            if belief is not None and view.legal_targets:
                marginals = marginal_mafia_probabilities(belief, view.num_players)
                values = [round(float(marginals[t]), 9) for t in view.legal_targets]
                samples.append(
                    {
                        "role": view.role,
                        "phase": view.phase,
                        "legal_targets": len(view.legal_targets),
                        "distinct_marginal_values": len(set(values)),
                        "flat": len(set(values)) == 1,
                        "top_marginal": max(values),
                    }
                )
            return target

    runner = SecretMafiaLiveRunner(
        discussion_rounds=discussion_rounds,
        policy_classes={"belief": _Probe},
        action_format=action_format,
        public_vote_record=public_vote_record,
    )
    belief_variant = next(
        variant for variant in DEFAULT_AB_VARIANTS if variant.variant_id == "belief"
    )
    for seed in range(seed_start, seed_start + episodes):
        runner.run_episode(variant=belief_variant, num_players=num_players, seed=seed)

    def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"decisions": 0, "flat_fraction": None, "mean_distinct_values": None}
        flat = sum(1 for row in rows if row["flat"])
        return {
            "decisions": len(rows),
            "flat_fraction": flat / len(rows),
            "mean_distinct_values": sum(
                row["distinct_marginal_values"] for row in rows
            )
            / len(rows),
            "mean_top_marginal": sum(row["top_marginal"] for row in rows) / len(rows),
        }

    by_role = {
        role: summarise([row for row in samples if row["role"] == role])
        for role in sorted({row["role"] for row in samples})
    }
    by_phase = {
        phase: summarise([row for row in samples if row["phase"] == phase])
        for phase in sorted({row["phase"] for row in samples})
    }
    return {
        "episodes": episodes,
        "num_players": num_players,
        "target_action_format": action_format,
        "reconstructed_public_vote_record": public_vote_record,
        "overall": summarise(samples),
        "by_role": by_role,
        "by_phase": by_phase,
        "interpretation": (
            "flat_fraction is the share of decisions where every legal target had "
            "the same marginal Mafia probability, so the belief could not rank "
            "them and the tie-break alone decided the action."
        ),
    }


def format_discrimination(report: dict[str, Any]) -> str:
    def fmt(value, spec=".3f"):
        return "n/a" if value is None else format(value, spec)

    lines = [
        f"belief discrimination over {report['episodes']} episodes, "
        f"{report['num_players']} players",
        f"  {'group':<22}{'decisions':>10}{'flat':>8}{'distinct':>10}{'top p':>8}",
    ]
    rows = [("overall", report["overall"])]
    rows += [(f"role:{k}", v) for k, v in report["by_role"].items()]
    rows += [(f"phase:{k}", v) for k, v in report["by_phase"].items()]
    for label, row in rows:
        lines.append(
            f"  {label:<22}{row['decisions']:>10}"
            f"{fmt(row['flat_fraction']):>8}"
            f"{fmt(row['mean_distinct_values'], '.2f'):>10}"
            f"{fmt(row['mean_top_marginal']):>8}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Paired cross-play against a fixed baseline
# ---------------------------------------------------------------------------

#: The fixed, uninformed opponent: uniform random legal target, no memory and no
#: belief.  It is frozen by definition and never learns from the informed seats.
BASELINE_VARIANT_ID = "plain"


def cross_play_conditions(
    informed_variant_id: str,
) -> dict[str, dict[str, str]]:
    """Seat plans for one informed policy against the fixed baseline.

    Each condition maps a seat role to the variant that drives it.  Roles, not
    seat ids, decide the arm, so the comparison is symmetric across seeds even
    though the role schedule changes.  Which seat holds which role is read from
    the seed's role schedule by the caller; that is experiment design, not
    information available to any policy.
    """
    baseline = BASELINE_VARIANT_ID
    informed = informed_variant_id
    return {
        "all_baseline": {role: baseline for role in _ROLE_ARMS},
        f"{informed}_village": {
            role: (baseline if role == "Mafia" else informed) for role in _ROLE_ARMS
        },
        f"{informed}_mafia": {
            role: (informed if role == "Mafia" else baseline) for role in _ROLE_ARMS
        },
        f"all_{informed}": {role: informed for role in _ROLE_ARMS},
    }


_ROLE_ARMS = ("Villager", "Mafia", "Doctor", "Detective")


def _variant_by_id(variant_id: str) -> VariantConfig:
    for variant in DEFAULT_AB_VARIANTS:
        if variant.variant_id == variant_id:
            return variant
    raise ValueError(f"unknown variant id: {variant_id}")


def seat_variants_for_condition(
    condition_plan: Mapping[str, str], role_schedule: Mapping[int, str]
) -> dict[int, VariantConfig]:
    out: dict[int, VariantConfig] = {}
    for pid, role in role_schedule.items():
        try:
            variant_id = condition_plan[role]
        except KeyError as exc:
            raise ValueError(f"condition plan has no arm for role {role}") from exc
        out[int(pid)] = _variant_by_id(variant_id)
    return out


_STEP_ID_RE = re.compile(r"^p(\d+)-n(\d+)-(.+)-(\d+)$")


def vote_coordination_report(episodes: Sequence[EpisodeEvaluation]) -> dict[str, Any]:
    """Measure how the day vote was actually distributed, per faction.

    This is the cross-play exploitability/asymmetry diagnostic peer decision 0016
    Q5 asks for.  It answers the question the win rates alone cannot: did the
    informed side win by *inferring* better, or by *coordinating* into a bloc
    while the opposing side scattered its votes?

    ``mafia_target_is_plurality_rate`` is the direct test.  The environment
    eliminates the plurality target, so if the Mafia's target is the (co-)plurality
    far more often than chance, the Mafia seats are effectively choosing the
    elimination rather than out-reasoning anyone.

    Read from already-recorded decisions; truth (the role schedule) is used only
    to label votes, never to produce them.
    """
    from collections import defaultdict

    rounds: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    mafia_by_episode: dict[int, set[int]] = {}
    for index, evaluation in enumerate(episodes):
        mafia_by_episode[index] = {
            int(pid) for pid in evaluation.metadata.get("true_mafia", [])
        }
        for checkpoint in evaluation.action_checkpoints:
            match = _STEP_ID_RE.match(checkpoint.step_id)
            if not match:
                continue
            actor, night, phase, _ = match.groups()
            if phase != "Day-Voting":
                continue
            kind, _, target = str(checkpoint.chosen_action_id).partition(":")
            if kind != "vote" or not target:
                continue
            rounds[(index, int(night))].append((int(actor), int(target)))

    mafia_rounds = 0
    union_mafia_rounds = 0
    plurality_rounds = 0
    distinct_mafia: list[int] = []
    distinct_village: list[int] = []
    for (index, _night), votes in rounds.items():
        mafia_seats = mafia_by_episode.get(index, set())
        mafia_votes = [target for actor, target in votes if actor in mafia_seats]
        village_votes = [target for actor, target in votes if actor not in mafia_seats]
        if len(mafia_votes) < 2:
            continue
        mafia_rounds += 1
        distinct_mafia.append(len(set(mafia_votes)))
        if village_votes:
            distinct_village.append(len(set(village_votes)))
        if len(set(mafia_votes)) == 1:
            union_mafia_rounds += 1
            counts: dict[int, int] = {}
            for target in [t for _a, t in votes]:
                counts[target] = counts.get(target, 0) + 1
            top = max(counts.values())
            if counts[mafia_votes[0]] == top:
                plurality_rounds += 1

    def rate(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    return {
        "day_vote_rounds_with_two_mafia_votes": mafia_rounds,
        "mafia_unanimous_rate": rate(union_mafia_rounds, mafia_rounds),
        "mafia_target_is_plurality_rate": rate(plurality_rounds, union_mafia_rounds),
        "mean_distinct_mafia_targets": _mean([float(x) for x in distinct_mafia]),
        "mean_distinct_village_targets": _mean([float(x) for x in distinct_village]),
        "interpretation": (
            "mafia_unanimous_rate is how often the two Mafia seats named the same "
            "target. mafia_target_is_plurality_rate is how often that shared "
            "target was then the (co-)plurality that the environment eliminates. "
            "A high pair means the informed Mafia wins by bloc voting, which is "
            "coordination, not inference."
        ),
    }


def aggregate_cross_play(episodes: Sequence[EpisodeEvaluation]) -> dict[str, Any]:
    """Score a cross-play condition by faction and by informed/baseline side.

    Which seats are informed is read per episode from that episode's seat plan,
    because the arm is assigned by role and the role schedule changes with the
    seed.  ``informed_faction_win_rate`` is only defined when exactly one faction
    holds informed seats; in ``all_baseline`` and ``all_<informed>`` it is
    reported as ``None`` rather than as a meaningless number.
    """
    if not episodes:
        raise ValueError("cannot aggregate a condition with no episodes")

    village_wins: list[float] = []
    informed_faction_wins: list[float] = []
    informed_faction_names: list[str] = []
    baseline_faction_wins: list[float] = []
    informed_seat_utilities: list[float] = []
    baseline_seat_utilities: list[float] = []
    leakage = 0
    brier_values: list[float] = []
    losses: list[float] = []

    for evaluation in episodes:
        rows = evaluation.metadata.get("actor_results", [])
        if not rows:
            continue
        role_by_pid = {int(row["actor_id"]): str(row["role"]) for row in rows}
        policy_by_pid = {
            int(pid): str(policy)
            for pid, policy in evaluation.metadata.get("seat_policy_by_actor", {}).items()
        }
        informed_seats = {
            pid for pid, policy in policy_by_pid.items() if policy != BASELINE_VARIANT_ID
        }
        baseline_seats = set(role_by_pid) - informed_seats

        village_seats = [row for row in rows if row["role"] != "Mafia"]
        village_won = 1.0 if all(row["won"] for row in village_seats) else 0.0
        village_wins.append(village_won)

        informed_roles = {role_by_pid[pid] for pid in informed_seats if pid in role_by_pid}
        if informed_roles and all(role != "Mafia" for role in informed_roles):
            informed_faction_wins.append(village_won)
            informed_faction_names.append("Village")
        elif informed_roles and all(role == "Mafia" for role in informed_roles):
            informed_faction_wins.append(1.0 - village_won)
            informed_faction_names.append("Mafia")

        if baseline_seats:
            baseline_roles = {
                role_by_pid[pid] for pid in baseline_seats if pid in role_by_pid
            }
            if baseline_roles == {"Mafia"}:
                baseline_faction_wins.append(1.0 - village_won)
            elif "Mafia" not in baseline_roles:
                baseline_faction_wins.append(village_won)

        informed_seat_utilities.extend(
            float(row["reward"])
            for row in rows
            if int(row["actor_id"]) in informed_seats and row["reward"] is not None
        )
        baseline_seat_utilities.extend(
            float(row["reward"])
            for row in rows
            if int(row["actor_id"]) in baseline_seats and row["reward"] is not None
        )

        summary = evaluation.summary()
        leakage += int(summary["information_leakage_count"])
        if summary["mean_brier"] is not None:
            brier_values.append(float(summary["mean_brier"]))
        for checkpoint in evaluation.action_checkpoints:
            losses.append(checkpoint.regret)

    village_rate = _mean(village_wins)
    return {
        "episodes": len(episodes),
        "village_faction_win_rate": village_rate,
        "mafia_faction_win_rate": (
            None if village_rate is None else 1.0 - village_rate
        ),
        "informed_faction_win_rate": _mean(informed_faction_wins),
        "informed_faction_episodes": len(informed_faction_wins),
        "informed_faction": (
            informed_faction_names[0]
            if informed_faction_names
            and len(set(informed_faction_names)) == 1
            else None
        ),
        "baseline_faction_win_rate": _mean(baseline_faction_wins),
        "informed_seat_mean_utility": _mean(informed_seat_utilities),
        "baseline_seat_mean_utility": _mean(baseline_seat_utilities),
        "mean_brier_village_side": _mean(brier_values),
        "information_leakage_count": leakage,
        "mean_immediate_target_loss_diagnostic": _mean(losses),
        "invalid_moves": sum(
            int(e.metadata.get("invalid_moves", 0)) for e in episodes
        ),
    }


def run_cross_play(
    *,
    informed_variant_ids: Sequence[str] = ("belief", "belief_planning"),
    episodes_per_condition: int = 50,
    num_players: int = 6,
    seed_start: int = 0,
    discussion_rounds: int = 3,
    action_format: str = DEFAULT_TARGET_ACTION_FORMAT,
    role_schedule_fn: Callable[..., dict[int, str]] | None = None,
    runner: SecretMafiaLiveRunner | None = None,
    progress: bool = False,
) -> dict[str, Any]:
    """Paired cross-play: informed seats against a frozen baseline.

    Every condition and every seed uses the identical role schedule, because the
    schedule is a deterministic function of the seed.  Each condition is scored
    by faction win rate and by the informed side's outcome, with the
    immediate-target-loss metric retained only as a diagnostic.
    """
    runner = runner or SecretMafiaLiveRunner(
        discussion_rounds=discussion_rounds, action_format=action_format
    )
    schedule_fn = role_schedule_fn or secret_mafia_role_schedule
    seeds = list(range(seed_start, seed_start + episodes_per_condition))
    schedules = {
        seed: schedule_fn(
            num_players=num_players,
            seed=seed,
            mafia_ratio=runner.mafia_ratio,
            discussion_rounds=discussion_rounds,
        )
        for seed in seeds
    }

    reference_id = "all_baseline"
    conditions: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    planned: list[tuple[str, dict[str, str] | None, str]] = [
        (reference_id, None, BASELINE_VARIANT_ID)
    ]
    for informed_id in informed_variant_ids:
        for condition_id, plan in cross_play_conditions(informed_id).items():
            if condition_id == reference_id:
                continue
            planned.append((condition_id, plan, informed_id))

    for condition_id, plan, label in planned:
        episodes: list[EpisodeEvaluation] = []
        started = time.perf_counter()
        for index, seed in enumerate(seeds):
            if plan is None:
                episodes.append(
                    runner.run_episode(
                        variant=_variant_by_id(BASELINE_VARIANT_ID),
                        condition_id=condition_id,
                        num_players=num_players,
                        seed=seed,
                    )
                )
            else:
                episodes.append(
                    runner.run_episode(
                        seat_variants=seat_variants_for_condition(
                            plan, schedules[seed]
                        ),
                        condition_id=condition_id,
                        num_players=num_players,
                        seed=seed,
                    )
                )
            if progress and (index + 1) % 50 == 0:
                print(f"  {condition_id}: {index + 1}/{len(seeds)}", flush=True)
        elapsed = time.perf_counter() - started
        row = aggregate_cross_play(episodes)
        row["informed_variant"] = label
        row["wall_clock_seconds"] = elapsed
        row["vote_coordination"] = vote_coordination_report(episodes)
        conditions[condition_id] = row
        for evaluation in episodes:
            records.append(episode_record(evaluation))
        if progress:
            print(f"  {condition_id}: done in {elapsed:.1f}s", flush=True)

    reference = conditions[reference_id]
    effects: dict[str, Any] = {}
    for informed_id in informed_variant_ids:
        village_row = conditions[f"{informed_id}_village"]
        mafia_row = conditions[f"{informed_id}_mafia"]
        all_row = conditions[f"all_{informed_id}"]
        effects[informed_id] = {
            "informed_village_vs_baseline_mafia": {
                "village_win_rate": village_row["village_faction_win_rate"],
                "baseline_village_win_rate": reference["village_faction_win_rate"],
                "village_delta": _delta(
                    village_row["village_faction_win_rate"],
                    reference["village_faction_win_rate"],
                ),
                "informed_faction_win_rate": village_row["informed_faction_win_rate"],
            },
            "informed_mafia_vs_baseline_village": {
                "mafia_win_rate": mafia_row["mafia_faction_win_rate"],
                "baseline_mafia_win_rate": reference["mafia_faction_win_rate"],
                "mafia_delta": _delta(
                    mafia_row["mafia_faction_win_rate"],
                    reference["mafia_faction_win_rate"],
                ),
                "informed_faction_win_rate": mafia_row["informed_faction_win_rate"],
            },
            "all_informed_self_play": {
                "village_win_rate": all_row["village_faction_win_rate"],
            },
            "asymmetry_note": (
                "Positive village_delta means informed village seats beat baseline "
                "Mafia more often than baseline village seats do. Positive "
                "mafia_delta is the mirror. A component that helps only one "
                "faction is asymmetric, not generally stronger."
            ),
        }

    return {
        "schema_version": 1,
        "status": "cross_play_run",
        "historical_world_writeback": False,
        "evidence_class": (
            "primary strength evidence per peer decision "
            "2026-10-11-0016-peer-decision-sck-methodology-next-gate Q2"
        ),
        "environment": {
            "primary": "TextArena SecretMafia",
            "textarena_version": _textarena_version(),
            "player_counts": [num_players],
            "discussion_rounds": discussion_rounds,
        },
        "design": {
            "episodes_per_condition": episodes_per_condition,
            "seeds": seeds,
            "same_seed_schedule_for_every_condition": True,
            "num_players": num_players,
            "baseline_variant": BASELINE_VARIANT_ID,
            "baseline_is_frozen": True,
            "target_action_format": action_format,
            "informed_policy_tie_break": runner.tie_break,
            "seat_assignment_uses_role_schedule": (
                "Arms are assigned by role, read from the seed's role schedule at "
                "setup time. This is experiment design, never an input to a "
                "policy: every decision still consumes only the seat's own "
                "ActorView."
            ),
            "role_schedule_check": _verify_cross_play_schedules(
                schedules, records, reference_id
            ),
        },
        "conditions": conditions,
        "cross_play_effect": effects,
        "episode_records": records,
        "reading_notes": [
            "Primary outcome is terminal cross-play faction win rate against the frozen baseline, not self-play win rate.",
            "mean_immediate_target_loss_diagnostic is a diagnostic only and must not be used as the acceptance metric.",
            "A condition whose informed side wins no more often than the all-baseline reference gives no evidence that the cognition component is stronger.",
        ],
    }


def _delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a - b


def _verify_cross_play_schedules(
    schedules: Mapping[int, Mapping[int, str]],
    records: Sequence[Mapping[str, Any]],
    reference_id: str,
) -> dict[str, Any]:
    """Every condition must have played the same role schedule for a given seed."""
    expected = {
        seed: sorted(pid for pid, role in schedule.items() if role == "Mafia")
        for seed, schedule in schedules.items()
    }
    mismatches = []
    per_condition: dict[str, int] = {}
    for record in records:
        condition = str(record.get("variant"))
        seed = record.get("seed")
        per_condition[condition] = per_condition.get(condition, 0) + 1
        if seed not in expected:
            mismatches.append({"condition": condition, "seed": seed, "reason": "unexpected seed"})
            continue
        if sorted(record.get("true_mafia") or []) != expected[seed]:
            mismatches.append(
                {
                    "condition": condition,
                    "seed": seed,
                    "observed_mafia": sorted(record.get("true_mafia") or []),
                    "expected_mafia": expected[seed],
                }
            )
    return {
        "verified": not mismatches,
        "reference_condition": reference_id,
        "seeds": len(expected),
        "episodes_checked": len(records),
        "episodes_per_condition": per_condition,
        "note": (
            "The role schedule is a deterministic function of the seed, so every "
            "condition shares it; this check confirms that from the recorded "
            "episodes rather than assuming it."
        ),
        "mismatches": mismatches,
    }


def format_cross_play(report: dict[str, Any]) -> str:
    def fmt(value, spec=".3f"):
        return "n/a" if value is None else format(value, spec)

    lines = [
        "SCK SecretMafia paired cross-play against a frozen baseline",
        f"  episodes per condition : {report['design']['episodes_per_condition']}",
        f"  players                : {report['design']['num_players']}",
        f"  baseline               : {report['design']['baseline_variant']} (frozen)",
        "",
        f"  {'condition':<26}{'village':>9}{'mafia':>8}{'informed':>10}{'loss(diag)':>12}{'leak':>6}",
    ]
    for condition_id, row in report["conditions"].items():
        lines.append(
            f"  {condition_id:<26}"
            f"{fmt(row['village_faction_win_rate']):>9}"
            f"{fmt(row['mafia_faction_win_rate']):>8}"
            f"{fmt(row['informed_faction_win_rate']):>10}"
            f"{fmt(row['mean_immediate_target_loss_diagnostic']):>12}"
            f"{row['information_leakage_count']:>6}"
        )
    lines.append("")
    lines.append("  informed = win rate of the single faction holding informed seats;")
    lines.append("             n/a in all_baseline and all_<informed>, where the label")
    lines.append("             would not identify one side.")
    lines.append("")
    lines.append("  vote coordination (explains how a win rate was obtained)")
    lines.append(
        f"  {'condition':<26}{'mafia unan.':>12}{'->plurality':>12}"
        f"{'m targets':>11}{'v targets':>11}"
    )
    for condition_id, row in report["conditions"].items():
        coord = row.get("vote_coordination") or {}
        lines.append(
            f"  {condition_id:<26}"
            f"{fmt(coord.get('mafia_unanimous_rate')):>12}"
            f"{fmt(coord.get('mafia_target_is_plurality_rate')):>12}"
            f"{fmt(coord.get('mean_distinct_mafia_targets'), '.2f'):>11}"
            f"{fmt(coord.get('mean_distinct_village_targets'), '.2f'):>11}"
        )
    lines.append("")
    lines.append("  cross-play effect vs the all_baseline reference")
    for informed_id, effect in report["cross_play_effect"].items():
        village = effect["informed_village_vs_baseline_mafia"]
        mafia = effect["informed_mafia_vs_baseline_village"]
        lines.append(
            f"  {informed_id:<17}"
            f"village delta {fmt(village['village_delta']):>7}   "
            f"mafia delta {fmt(mafia['mafia_delta']):>7}"
        )
    return "\n".join(lines)


def _textarena_version() -> str:
    try:
        import importlib.metadata  # noqa: PLC0415

        return importlib.metadata.version("textarena")
    except Exception:  # pragma: no cover - depends on environment
        return "unknown"


def format_report(report: dict[str, Any]) -> str:
    def fmt(value, spec=".3f"):
        return "n/a" if value is None else format(value, spec)

    lines = [
        "SCK SecretMafia A/B smoke test",
        f"  episodes per variant : {report['design']['episodes_per_variant']}",
        f"  players              : {report['design']['num_players']}",
        f"  shared role schedule : {report['design']['role_schedule_check']['verified']}",
        "",
        f"  {'variant':<17}{'regret':>8}{'brier':>9}{'leak':>6}{'village':>9}{'mafia':>8}",
    ]
    for variant_id, row in report["variants"].items():
        lines.append(
            f"  {variant_id:<17}"
            f"{fmt(row['mean_immediate_target_loss_diagnostic']):>8}"
            f"{fmt(row['mean_brier_village_side'], '.4f'):>9}"
            f"{row['information_leakage_count']:>6}"
            f"{fmt(row['village_faction_win_rate']):>9}"
            f"{fmt(row['mafia_faction_win_rate']):>8}"
        )
    lines.append("")
    lines.append("  loss   = mean immediate-target loss, DIAGNOSTIC ONLY (peer 0016 Q5): it")
    lines.append("           ignores coordination and future response and can improve while")
    lines.append("           terminal play gets worse, so it is not a quality verdict")
    lines.append("  brier  = village-side belief calibration (lower better, n/a = no belief)")
    lines.append("  village/mafia = faction win rate in self-play (descriptive, not the claim)")
    lines.append("")
    lines.append("  immediate-target loss by kind (diagnostic)")
    for variant_id, row in report["variants"].items():
        kinds = ", ".join(
            f"{kind}={value:.3f}"
            for kind, value in row["immediate_target_loss_by_kind_diagnostic"].items()
        )
        lines.append(f"  {variant_id:<17}{kinds}")
    lines.append("")
    lines.append("  per-role self-play win rate")
    for variant_id, row in report["variants"].items():
        roles = ", ".join(
            f"{role}={entry['won']}/{entry['played']}"
            for role, entry in sorted(row["per_role"].items())
        )
        lines.append(f"  {variant_id:<17}{roles}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--players", type=int, default=6)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--discussion-rounds", type=int, default=3)
    parser.add_argument(
        "--tie-break",
        choices=("lowest_id", "random"),
        default="lowest_id",
        help="Tie-break for informed policies; lowest_id keeps the planner ablation clean.",
    )
    parser.add_argument(
        "--action-format",
        choices=TARGET_ACTION_FORMATS,
        default=DEFAULT_TARGET_ACTION_FORMAT,
        help=(
            "Target action encoding. 'native' submits [N], whose target survives "
            "the public observation stream. 'player_tag' submits [Player N], which "
            "the environment strips to an empty string; kept for comparison only."
        ),
    )
    parser.add_argument(
        "--public-vote-record",
        action="store_true",
        help=(
            "Labelled sensitivity arm: reconstruct the vote record that the "
            "legacy player_tag encoding destroys. Forces --action-format "
            "player_tag, because the native format already makes votes visible."
        ),
    )
    parser.add_argument(
        "--out", type=Path, default=None
    )
    parser.add_argument(
        "--diagnose-discrimination",
        type=int,
        default=0,
        metavar="N",
        help="Also measure, over N belief episodes, how often the belief could rank the legal targets.",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--cross-play",
        action="store_true",
        help=(
            "Run paired cross-play against the frozen baseline instead of "
            "all-seats self-play. This is the primary strength evidence."
        ),
    )
    args = parser.parse_args(argv)

    action_format = args.action_format
    if args.public_vote_record and action_format == "native":
        print(
            "note: --public-vote-record reconstructs what the legacy player_tag "
            "encoding destroys, so this run uses action_format=player_tag.",
            flush=True,
        )
        action_format = "player_tag"

    # Fail early and clearly if the live dependency is missing.
    load_textarena_secret_mafia_env()

    if args.cross_play:
        report = run_cross_play(
            episodes_per_condition=args.episodes,
            num_players=args.players,
            seed_start=args.seed_start,
            discussion_rounds=args.discussion_rounds,
            action_format=action_format,
            progress=not args.quiet,
        )
        print(format_cross_play(report))
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8"
            )
            print(f"\nwrote {args.out}")
        return 0

    report = run_ab(
        episodes_per_variant=args.episodes,
        num_players=args.players,
        seed_start=args.seed_start,
        discussion_rounds=args.discussion_rounds,
        tie_break=args.tie_break,
        action_format=action_format,
        public_vote_record=args.public_vote_record,
        progress=not args.quiet,
    )
    if args.diagnose_discrimination:
        report["belief_discrimination"] = discrimination_report(
            episodes=args.diagnose_discrimination,
            num_players=args.players,
            seed_start=args.seed_start,
            discussion_rounds=args.discussion_rounds,
            action_format=action_format,
            public_vote_record=args.public_vote_record,
        )
    print(format_report(report))
    if args.diagnose_discrimination:
        print()
        print(format_discrimination(report["belief_discrimination"]))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
