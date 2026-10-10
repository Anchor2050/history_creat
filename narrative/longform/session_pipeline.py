"""Session engineering target: audit, run 32x160, mine candidates, judge readiness."""
from copy import deepcopy

from .endogenous_world import simulate_endogenous_world
from .macro_world import beijing_2026_macro
from .multiverse import _inject_seeded_shocks, world_specs
from .story_miner import pareto_mine


def _macro_for(spec):
    return _inject_seeded_shocks(beijing_2026_macro(), spec)


def run_session_pipeline(count=32, weeks=160, master_seed=20261011):
    specs = world_specs(count, master_seed)
    runs = []
    for spec in specs:
        # External social events use the world seed. Macro variation follows family.
        run = simulate_endogenous_world(spec["seed"], weeks, _macro_for(spec))
        run["spec"] = deepcopy(spec)
        runs.append(run)
    candidates = pareto_mine(runs, min(8, count))
    audit = audit_runs(runs)
    return {
        "version": 1, "count": count, "weeks": weeks,
        "world_weeks": count * weeks, "master_seed": master_seed,
        "audit": audit, "candidates": candidates, "runs": runs,
        "status": "complete_requires_deep_replay" if audit["passes"] else "complete_audit_failed",
    }


def audit_runs(runs):
    total_chains = sum(len(r["cross_actor_chains"]) for r in runs)
    worlds_with_chain = sum(bool(r["cross_actor_chains"]) for r in runs)
    worlds_with_lifecycle = sum(bool(r["lifecycle"]) for r in runs)
    negative_cash_worlds = sum(not r["no_negative_cash"] for r in runs)
    seeded_events_logged = all(all(e.get("provenance", {}).get("kind") == "seeded_exogenous_event" for e in r["external_events"]) for r in runs)
    # This is an engineering readiness gate, not a literary-quality claim.
    passes = (
        len(runs) > 0 and worlds_with_lifecycle == len(runs)
        and seeded_events_logged and total_chains > 0
        and negative_cash_worlds <= len(runs) // 4
    )
    return {
        "worlds": len(runs), "total_cross_actor_chains": total_chains,
        "worlds_with_cross_actor_chain": worlds_with_chain,
        "worlds_with_lifecycle_change": worlds_with_lifecycle,
        "negative_cash_worlds": negative_cash_worlds,
        "seeded_external_events_all_logged": seeded_events_logged,
        "passes": passes,
    }
