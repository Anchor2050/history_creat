"""Mine long histories for structurally promising replay candidates.

The miner never changes history and never collapses quality to one drama score.
It rewards causal depth and delayed consequences while explicitly penalizing
coincidence stacking, unsupported shocks and repeated crisis density.
"""
from collections import Counter


def features(run):
    topology = run.get("topology", {})
    nodes = topology.get("nodes", [])
    chains = run.get("cross_actor_chains", [])
    lifecycle = run.get("lifecycle", [])
    external = run.get("external_events", [])
    weeks = max(1, run.get("weeks", 1))
    actors = set()
    for n in nodes:
        if n.get("actor"): actors.add(n["actor"])
        if n.get("target") in {"lin_jing", "chen_lan", "xu_hang", "zhao_ke"}: actors.add(n["target"])
    max_trace = max([c.get("trace_length", 0) for c in chains] or [0])
    cross_actor = len(chains)
    delayed = sum(1 for c in chains if c.get("end_week", 0) >= 26)
    irreversible = len(lifecycle)
    resource_domains = len({c.get("resource") for c in chains if c.get("resource")})
    event_density = len(nodes) / weeks
    external_density = len(external) / weeks
    repeated = Counter(e.get("kind") for e in external)
    coincidence_penalty = max(0.0, external_density - 0.12) + 0.03 * sum(max(0, n - 4) for n in repeated.values())
    crisis_penalty = max(0.0, event_density - 0.45)
    unsupported = sum(1 for n in nodes if n.get("causes") == [] and n.get("kind") not in {
        "exogenous_household_event", "shared_resource_allocated", "career_path_changed"
    })
    unsupported_penalty = unsupported / max(1, len(nodes))
    return {
        "causal_depth": min(1.0, max_trace / 8.0),
        "cross_actor_consequence": min(1.0, cross_actor / 5.0),
        "delayed_consequence": min(1.0, delayed / 3.0),
        "irreversibility": min(1.0, irreversible / 3.0),
        "ensemble_depth": min(1.0, len(actors) / 4.0),
        "institution_private_collision": min(1.0, resource_domains / 4.0),
        "coincidence_penalty": round(min(1.0, coincidence_penalty), 4),
        "crisis_density_penalty": round(min(1.0, crisis_penalty), 4),
        "unsupported_causality_penalty": round(min(1.0, unsupported_penalty), 4),
    }


def _dominates(a, b, rewards, penalties):
    no_worse = all(a[k] >= b[k] for k in rewards) and all(a[k] <= b[k] for k in penalties)
    better = any(a[k] > b[k] for k in rewards) or any(a[k] < b[k] for k in penalties)
    return no_worse and better


def pareto_mine(runs, limit=8):
    rewards = ("causal_depth", "cross_actor_consequence", "delayed_consequence", "irreversibility", "ensemble_depth", "institution_private_collision")
    penalties = ("coincidence_penalty", "crisis_density_penalty", "unsupported_causality_penalty")
    rows = [{"run": r, "features": features(r)} for r in runs]
    frontier = []
    for row in rows:
        if not any(other is not row and _dominates(other["features"], row["features"], rewards, penalties) for other in rows):
            frontier.append(row)
    frontier.sort(key=lambda x: (x["run"].get("seed", 0), x["run"].get("spec", {}).get("world_id", "")))
    chosen = frontier[:limit]
    if len(chosen) < limit:
        used = {id(x["run"]) for x in chosen}
        rest = [x for x in rows if id(x["run"]) not in used]
        # Fill for structural diversity, still without a weighted drama scalar.
        axes = list(rewards)
        while rest and len(chosen) < limit:
            axis = axes[len(chosen) % len(axes)]
            rest.sort(key=lambda x: (-x["features"][axis], x["features"]["coincidence_penalty"], x["run"].get("seed", 0)))
            chosen.append(rest.pop(0))
    return chosen
