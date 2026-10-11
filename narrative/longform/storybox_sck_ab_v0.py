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

* ``mean_action_regret_by_kind`` -- per-decision quality against a truth oracle
  (``+1`` faction-optimal, ``-1`` faction-worst target), which is the only
  per-decision quality signal available here;
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
import time
from typing import Any, Iterable, Sequence

from .storybox_sck_eval_v0 import DEFAULT_AB_VARIANTS, EpisodeEvaluation, VariantConfig
from .storybox_textarena_secret_mafia_live_v0 import (
    BeliefPolicy,
    SecretMafiaLiveRunner,
    load_textarena_secret_mafia_env,
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
        "textarena 0.7.4 strips role tags from PLAYER_ACTION messages, so vote "
        "targets are unobservable and no vote evidence metric exists."
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
        "mean_action_regret": _mean(all_regrets),
        "mean_action_regret_by_kind": regret_means,
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
        "mean_action_regret": mean_regret,
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
    public_vote_record: bool = False,
    runner: SecretMafiaLiveRunner | None = None,
    progress: bool = False,
) -> dict[str, Any]:
    variants = tuple(variants or DEFAULT_AB_VARIANTS)
    runner = runner or SecretMafiaLiveRunner(
        discussion_rounds=discussion_rounds,
        tie_break=tie_break,
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
            "reconstructed_public_vote_record": public_vote_record,
            "role_schedule_check": role_check,
        },
        "variants": variant_reports,
        "episode_records": episode_records,
        "failure_replay_retention": (
            "episode_records holds one compact record per episode (seed, role "
            "schedule, outcome, steps, regret, calibration, leakage), which is the "
            "replay depth available in a run with no model calls."
        ),
        "unavailable_metrics": UNAVAILABLE_METRICS,
        "non_discriminating_metrics": {
            "mean_action_regret_by_kind.mafia_eliminate": (
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
            f"{fmt(row['mean_action_regret']):>8}"
            f"{fmt(row['mean_brier_village_side'], '.4f'):>9}"
            f"{row['information_leakage_count']:>6}"
            f"{fmt(row['village_faction_win_rate']):>9}"
            f"{fmt(row['mafia_faction_win_rate']):>8}"
        )
    lines.append("")
    lines.append("  regret = mean action regret vs truth oracle (lower is better)")
    lines.append("  brier  = village-side belief calibration (lower better, n/a = no belief)")
    lines.append("  village/mafia = faction win rate in self-play (descriptive, not the claim)")
    lines.append("")
    lines.append("  action regret by kind")
    for variant_id, row in report["variants"].items():
        kinds = ", ".join(
            f"{kind}={value:.3f}"
            for kind, value in row["mean_action_regret_by_kind"].items()
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
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--public-vote-record",
        action="store_true",
        help=(
            "Labelled sensitivity arm: reconstruct the day-vote record the "
            "environment destroys before broadcasting it. Off by default so "
            "primary numbers stay strictly within what the environment delivers."
        ),
    )
    parser.add_argument(
        "--diagnose-discrimination",
        type=int,
        default=0,
        metavar="N",
        help="Also measure, over N belief episodes, how often the belief could rank the legal targets.",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    # Fail early and clearly if the live dependency is missing.
    load_textarena_secret_mafia_env()

    report = run_ab(
        episodes_per_variant=args.episodes,
        num_players=args.players,
        seed_start=args.seed_start,
        discussion_rounds=args.discussion_rounds,
        tie_break=args.tie_break,
        public_vote_record=args.public_vote_record,
        progress=not args.quiet,
    )
    if args.diagnose_discrimination:
        report["belief_discrimination"] = discrimination_report(
            episodes=args.diagnose_discrimination,
            num_players=args.players,
            seed_start=args.seed_start,
            discussion_rounds=args.discussion_rounds,
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
