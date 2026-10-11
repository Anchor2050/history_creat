"""Continuity pass v2 for the six-character 2026-2035 branch.

This module keeps career_six_2035.py as a frozen baseline and strengthens three
things: continuous 2029-2031 search, causal shared-capacity conflicts, and
bidirectional costs/benefits between the added cohort and the original cast.
"""
from copy import deepcopy
import random

from . import career_six_2035 as base

JOB_CYCLE_YEARS = tuple(range(2026, 2032))


def _topology(design):
    topology = base._topology(design)
    # One high-touch public-sector mock/interview slot creates a real shared
    # opportunity bottleneck. Ordinary preparation remains outside this resource.
    topology.state["resources"]["career.public_sector_mock_interview"]["capacity"] = 1.0
    return topology


def _initial_state(design, rng):
    actors, originals = base._initial_state(design, rng)
    for actor in actors.values():
        actor["blocked_cycles"] = 0
        actor["target_revision_count"] = 0
    originals["lin_jing"]["time_pressure"] = .35
    originals["chen_lan"]["time_pressure"] = .52
    originals["xu_hang"]["time_pressure"] = .40
    return actors, originals


def _interactions(actors, originals, topology, year, month):
    rows = base._interactions(actors, originals, topology, year, month)
    # Networking is not free. Each substantive exchange consumes some of the
    # original character's discretionary capacity even when it expands options.
    for row in rows:
        old = row["existing_actor"]
        if old in originals:
            originals[old]["time_pressure"] = min(
                1.0, originals[old]["time_pressure"] + .004
            )
    return rows


def _allocate(actor_id, actor, topology, when):
    resource_id = base.TARGET_RESOURCE[actor["current_target"]]
    amount = 8.0 if resource_id.endswith("project_hours") else 1.0
    if topology.resource_available(resource_id) + 1e-12 < amount:
        holders = sorted(topology.state["resources"][resource_id]["allocations"])
        causes = [
            node["id"]
            for node in topology.state["nodes"]
            if node["kind"] == "shared_resource_allocated"
            and node["target"] == resource_id
            and node["actor"] in holders
        ][-3:]
        node = topology._node(
            "career_option_blocked_by_shared_capacity",
            when,
            actor=actor_id,
            target=resource_id,
            payload={"current_target": actor["current_target"], "holders": holders},
            causes=causes,
        )
        return False, node["id"], holders
    node = topology.allocate(resource_id, actor_id, amount, when)
    return True, node["id"], []


def _maybe_revise_target(actor_id, actor, topology, rng, year, month, cause_node):
    pressure = actor["failed_cycles"] + actor["blocked_cycles"]
    if year < 2028 or pressure < 2 or actor["target_revision_count"] >= 2:
        return None
    if rng.random() >= .62:
        return None
    options = [
        target for target in base.FALLBACK_TARGETS[actor_id]
        if target != actor["current_target"]
    ]
    if not options:
        return None
    old = actor["current_target"]
    actor["current_target"] = rng.choice(options)
    actor["target_revision_count"] += 1
    actor["failed_cycles"] = 0
    actor["blocked_cycles"] = 0
    node = topology._node(
        "career_target_revised_after_accumulated_pressure",
        base._when(year, month),
        actor=actor_id,
        target=actor["current_target"],
        payload={
            "from": old,
            "to": actor["current_target"],
            "revision_count": actor["target_revision_count"],
        },
        causes=[cause_node],
    )
    actor["history"].append({
        "date": base._when(year, month),
        "event": "career_target_revised",
        "from": old,
        "to": actor["current_target"],
        "node": node["id"],
    })
    return node["id"]


def _backprop_accepted_job(actor_id, actor, originals, topology, when, cause_node):
    old_actor = None
    if actor_id in ("gao_yuan", "he_xin", "luo_cheng"):
        old_actor = "lin_jing"
        originals[old_actor]["public_sector_option"] = min(
            1.0, originals[old_actor]["public_sector_option"] + .018
        )
    elif actor_id == "song_nan":
        old_actor = "chen_lan"
        originals[old_actor]["health_data_translation"] = min(
            1.0, originals[old_actor]["health_data_translation"] + .025
        )
    elif actor_id in ("zhou_ye", "tang_yu"):
        old_actor = "xu_hang"
        originals[old_actor]["verification_reputation"] = min(
            1.0, originals[old_actor]["verification_reputation"] + .020
        )
    if old_actor is None:
        return None
    originals[old_actor]["network"] = min(1.0, originals[old_actor]["network"] + .010)
    return topology._node(
        "cross_cohort_outcome_backpropagated",
        when,
        actor=actor_id,
        target=old_actor,
        payload={"new_actor": actor_id, "sector": actor["sector"]},
        causes=[cause_node],
    )["id"]


def _job_cycle(actors, originals, topology, rng, year, month):
    if month != 10 or year not in JOB_CYCLE_YEARS:
        return []
    base._reset(topology, base._when(year, month))
    rows = []
    candidates = [
        actor_id for actor_id in base.NEW_ACTORS
        if actors[actor_id]["stage"] in ("doctoral", "search")
    ]
    candidates.sort(key=lambda actor_id: (-base._score(actors[actor_id]), actor_id))
    for actor_id in candidates:
        actor = actors[actor_id]
        ok, resource_node, holders = _allocate(
            actor_id, actor, topology, base._when(year, month)
        )
        score = base._score(actor)
        if not ok:
            actor["stage"] = "search"
            actor["blocked_cycles"] += 1
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .02)
            actor["history"].append({
                "date": base._when(year, month),
                "event": "resource_blocked",
                "target": actor["current_target"],
                "holders": holders,
                "node": resource_node,
            })
            revision = _maybe_revise_target(
                actor_id, actor, topology, rng, year, month, resource_node
            )
            rows.append({
                "date": base._when(year, month),
                "actor": actor_id,
                "outcome": "blocked",
                "node": resource_node,
                "holders": holders,
                "revised_to": actor["current_target"] if revision else None,
            })
            continue

        threshold = rng.uniform(.62, .84) + .010 * max(0, year - 2026)
        if score >= threshold:
            actor.update(
                stage="employed",
                sector=actor["current_target"],
                failed_cycles=0,
                blocked_cycles=0,
            )
            actor["stability"] = min(1.0, .58 + .20 * score)
            actor["mobility"] = max(.30, actor["mobility"] - .08)
            actor["career_satisfaction"] = min(
                1.0, .48 + .28 * score + rng.uniform(-.08, .08)
            )
            node = topology._node(
                "first_job_accepted",
                base._when(year, month),
                actor=actor_id,
                target=actor["sector"],
                payload={"score": round(score, 4)},
                causes=[resource_node],
            )
            _backprop_accepted_job(
                actor_id, actor, originals, topology, base._when(year, month), node["id"]
            )
            outcome = "accepted"
        else:
            actor["stage"] = "search"
            actor["failed_cycles"] += 1
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .04)
            node = topology._node(
                "job_cycle_failed",
                base._when(year, month),
                actor=actor_id,
                target=actor["current_target"],
                payload={"score": round(score, 4), "failed_cycles": actor["failed_cycles"]},
                causes=[resource_node],
            )
            outcome = "failed"
            _maybe_revise_target(actor_id, actor, topology, rng, year, month, node["id"])
        actor["history"].append({
            "date": base._when(year, month),
            "event": outcome,
            "target": actor["current_target"],
        })
        rows.append({
            "date": base._when(year, month),
            "actor": actor_id,
            "outcome": outcome,
            "node": node["id"],
            "score": round(score, 4),
        })
    return rows


def _reentry(actors, originals, topology, rng, year, month):
    if month != 10 or year not in (2032, 2034):
        return []
    base._reset(topology, base._when(year, month))
    rows = []
    for actor_id, actor in actors.items():
        if actor["stage"] != "search":
            continue
        ok, resource_node, holders = _allocate(
            actor_id, actor, topology, base._when(year, month)
        )
        if not ok:
            rows.append({
                "date": base._when(year, month),
                "actor": actor_id,
                "outcome": "blocked",
                "holders": holders,
                "node": resource_node,
            })
            continue
        score = base._score(actor) + rng.uniform(-.04, .05)
        if score >= rng.uniform(.62, .82):
            old = actor["sector"]
            actor.update(
                stage="employed",
                sector=actor["current_target"],
                failed_cycles=0,
                blocked_cycles=0,
            )
            actor["career_satisfaction"] = min(1.0, .48 + .25 * score)
            node = topology._node(
                "midcareer_reentry",
                base._when(year, month),
                actor=actor_id,
                target=actor["sector"],
                payload={"from": old, "score": round(score, 4)},
                causes=[resource_node],
            )
            _backprop_accepted_job(
                actor_id, actor, originals, topology, base._when(year, month), node["id"]
            )
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "accepted", "node": node["id"],
            })
        else:
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "failed", "node": resource_node,
            })
    return rows


def simulate_career_six_continuity(seed=1, design=None):
    """Run continuity-v2 without mutating the v1 baseline implementation."""
    design = deepcopy(design or base.load_career_six_design())
    rng = random.Random(seed)
    topology = _topology(design)
    actors, originals = _initial_state(design, rng)
    interactions, jobs, family, reassessments, reentries, snapshots = [], [], [], [], [], []

    for year, month in base._months():
        for actor in actors.values():
            if actor["stage"] in ("doctoral", "search"):
                for key, delta in (
                    ("technical", .0020), ("exam", .0015),
                    ("research", .0016), ("translation", .0014),
                ):
                    actor["readiness"][key] = min(1.0, actor["readiness"][key] + delta)
            elif actor["sector"] == "university_faculty":
                actor["readiness"]["research"] = min(
                    1.0, actor["readiness"]["research"] + .0022
                )
            elif actor["sector"] == "pharmaceutical_industry":
                actor["readiness"]["translation"] = min(
                    1.0, actor["readiness"]["translation"] + .0024
                )
            else:
                actor["readiness"]["translation"] = min(
                    1.0, actor["readiness"]["translation"] + .0012
                )

        interactions.extend(_interactions(actors, originals, topology, year, month))
        jobs.extend(_job_cycle(actors, originals, topology, rng, year, month))
        family.extend(base._family_pressure(actors, topology, rng, year, month))
        reassessments.extend(base._reassess(actors, originals, topology, rng, year, month))
        reentries.extend(_reentry(actors, originals, topology, rng, year, month))

        if month == 12:
            snapshots.append({
                "year": year,
                "actors": deepcopy(actors),
                "original_core": deepcopy(originals),
            })

    capacity_conflicts = [
        row for row in jobs + reentries if row.get("outcome") == "blocked"
    ]
    return {
        "seed": seed,
        "status": "career_six_2026_2035_continuity_v2_noncanonical_scout",
        "start_date": design["start_date"],
        "end_date": design["end_date"],
        "actors": actors,
        "original_core": originals,
        "interactions": interactions,
        "job_cycles": jobs,
        "family_events": family,
        "reassessments": reassessments,
        "reentries": reentries,
        "capacity_conflicts": capacity_conflicts,
        "annual_snapshots": snapshots,
        "topology": topology.snapshot(),
        "fixed_design_rules": deepcopy(design["fixed_design_rules"]),
    }
