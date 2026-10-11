"""2026-2035 scouting world for six added doctoral characters.

The six-character cohort is an extension of the existing Beijing long-form world.
It is deliberately non-canonical: fixed user-supplied starting facts are kept
stable while job outcomes, family bargains, moves and later career changes are
seeded branches. Existing characters remain active causal participants.
"""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import random

from .consequence_topology import ConsequenceTopology, DEFAULT_TOPOLOGY


NEW_ACTORS = (
    "zhou_ye", "gao_yuan", "luo_cheng", "tang_yu", "he_xin", "song_nan"
)
ORIGINAL_CORE = ("lin_jing", "chen_lan", "xu_hang")
ORIGINAL_GATEKEEPERS = ("wu_cheng", "shen_yan", "gu_wei", "zhao_ke", "sun_jie")
ALL_EXISTING = ORIGINAL_CORE + ORIGINAL_GATEKEEPERS

TARGET_RESOURCE = {
    "state_owned_enterprise": "career.state_owned_enterprise_referral",
    "civil_service": "career.public_sector_mock_interview",
    "university_counselor": "career.university_counselor_referral",
    "university_faculty": "career.university_faculty_referral",
    "civil_service_or_public_institution": "career.public_sector_mock_interview",
    "pharmaceutical_industry": "career.pharma_statistics_project_hours",
}

BASE_READINESS = {
    "zhou_ye": {"technical": .68, "exam": .30, "research": .34, "translation": .38},
    "gao_yuan": {"technical": .60, "exam": .58, "research": .30, "translation": .35},
    "luo_cheng": {"technical": .55, "exam": .48, "research": .28, "translation": .52},
    "tang_yu": {"technical": .66, "exam": .32, "research": .62, "translation": .44},
    "he_xin": {"technical": .62, "exam": .56, "research": .50, "translation": .43},
    "song_nan": {"technical": .67, "exam": .30, "research": .52, "translation": .62},
}

INTERACTION_RULES = (
    ("zhou_ye", "xu_hang", "technical", .025, "research_reliability"),
    ("gao_yuan", "lin_jing", "exam", .030, "public_sector_preparation"),
    ("luo_cheng", "sun_jie", "translation", .035, "student_affairs_reality"),
    ("tang_yu", "shen_yan", "research", .030, "methods_feedback"),
    ("he_xin", "lin_jing", "exam", .020, "career_comparison"),
    ("he_xin", "sun_jie", "exam", .025, "public_institution_process"),
    ("song_nan", "chen_lan", "translation", .030, "industry_translation"),
    ("song_nan", "zhao_ke", "translation", .035, "project_channel"),
    ("tang_yu", "xu_hang", "research", .020, "verification_collaboration"),
    ("zhou_ye", "chen_lan", "translation", .015, "stable_work_comparison"),
    ("luo_cheng", "lin_jing", "translation", .015, "university_path_comparison"),
)

TARGET_WEIGHTS = {
    "state_owned_enterprise": {"technical": .45, "translation": .25, "exam": .15, "research": .15},
    "civil_service": {"exam": .55, "translation": .20, "technical": .15, "research": .10},
    "university_counselor": {"translation": .45, "exam": .25, "technical": .15, "research": .15},
    "university_faculty": {"research": .55, "technical": .25, "translation": .15, "exam": .05},
    "civil_service_or_public_institution": {"exam": .45, "translation": .30, "technical": .15, "research": .10},
    "pharmaceutical_industry": {"technical": .30, "translation": .35, "research": .30, "exam": .05},
}


def _month_iter(start=(2026, 3), end=(2035, 12)):
    y, m = start
    while (y, m) <= end:
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def _when(year, month):
    return date(year, month, 1).isoformat()


def load_career_six_design(path=None):
    if path is None:
        path = (
            Path(__file__).resolve().parents[2]
            / "docs" / "scenarios" / "career-six-2026-2035-v1.json"
        )
    with open(path, "r", encoding="utf-8") as handle:
        design = json.load(handle)
    if design.get("spec_version") != 1:
        raise ValueError("career-six scenario requires spec_version 1")
    if tuple(design.get("actors", {}).keys()) != NEW_ACTORS:
        raise ValueError("career-six scenario must contain the six fixed actor ids in order")
    return design


def _topology(design):
    state = deepcopy(DEFAULT_TOPOLOGY)
    for actor_id, actor in design["actors"].items():
        state["actor_status"][actor_id] = {
            "active": True,
            "institution": actor["organization"],
        }
    state["resources"].update({
        "career.citywide_doctoral_job_information": {"capacity": 6.0, "allocations": {}},
        "career.public_sector_mock_interview": {"capacity": 2.0, "allocations": {}},
        "career.university_faculty_referral": {"capacity": 1.0, "allocations": {}},
        "career.university_counselor_referral": {"capacity": 1.0, "allocations": {}},
        "career.state_owned_enterprise_referral": {"capacity": 1.0, "allocations": {}},
        "career.pharma_statistics_project_hours": {"capacity": 40.0, "allocations": {}},
    })
    return ConsequenceTopology(state)


def _initial_state(design, rng):
    actors = {}
    for actor_id, row in design["actors"].items():
        family_share = (
            rng.uniform(.72, .98)
            if row.get("only_child")
            else rng.uniform(.22, .68)
        )
        actors[actor_id] = {
            "id": actor_id,
            "name": row["name"],
            "field": row["field"],
            "target_2026": row["career_target_2026"],
            "current_target": row["career_target_2026"],
            "stage": "doctoral",
            "sector": None,
            "city_state": "beijing_training",
            "cash": float(row["cash"]),
            "readiness": deepcopy(BASE_READINESS[actor_id]),
            "network": .30,
            "stability": .20,
            "mobility": .78,
            "family_care_share": family_share,
            "family_care_load": 0.0,
            "career_satisfaction": .50,
            "publication_count_fixed": row.get("published_papers"),
            "history": [],
        }
    originals = {
        "lin_jing": {"public_sector_option": .20, "network": .45, "mobility": .74},
        "chen_lan": {"health_data_translation": .20, "network": .50, "mobility": .62},
        "xu_hang": {"verification_reputation": .42, "network": .38, "mobility": .70},
    }
    return actors, originals


def _reset_cycle_resources(topology, when):
    for rid in (
        "career.public_sector_mock_interview",
        "career.university_faculty_referral",
        "career.university_counselor_referral",
        "career.state_owned_enterprise_referral",
        "career.pharma_statistics_project_hours",
    ):
        row = topology.state["resources"][rid]
        holders = list(row["allocations"].items())
        for actor_id, amount in holders:
            topology.release(rid, actor_id, amount, when)


def _apply_interactions(actors, originals, topology, year, month):
    if month not in (3, 9):
        return []
    out = []
    for new_actor, old_actor, dimension, delta, domain in INTERACTION_RULES:
        actor = actors[new_actor]
        if actor["stage"] == "inactive":
            continue
        actor["readiness"][dimension] = min(1.0, actor["readiness"][dimension] + delta)
        actor["network"] = min(1.0, actor["network"] + .012)
        if old_actor in originals:
            if old_actor == "lin_jing":
                originals[old_actor]["public_sector_option"] = min(
                    1.0, originals[old_actor]["public_sector_option"] + .012
                )
            elif old_actor == "chen_lan":
                originals[old_actor]["health_data_translation"] = min(
                    1.0, originals[old_actor]["health_data_translation"] + .012
                )
            elif old_actor == "xu_hang":
                originals[old_actor]["verification_reputation"] = min(
                    1.0, originals[old_actor]["verification_reputation"] + .012
                )
            originals[old_actor]["network"] = min(
                1.0, originals[old_actor]["network"] + .006
            )
        node = topology.update_reputation(
            old_actor, new_actor, domain, .025, _when(year, month)
        )
        out.append({
            "date": _when(year, month),
            "kind": "cross_cohort_interaction",
            "new_actor": new_actor,
            "existing_actor": old_actor,
            "domain": domain,
            "node": node["id"],
        })
    return out


def _score(actor):
    weights = TARGET_WEIGHTS[actor["current_target"]]
    return sum(actor["readiness"][k] * w for k, w in weights.items()) + .12 * actor["network"]


def _allocate_target_resource(actor_id, actor, topology, when):
    rid = TARGET_RESOURCE[actor["current_target"]]
    amount = 8.0 if rid.endswith("project_hours") else 1.0
    if topology.resource_available(rid) + 1e-12 < amount:
        node = topology._node(
            "career_option_blocked_by_shared_capacity",
            when, actor=actor_id, target=rid,
            payload={"current_target": actor["current_target"]},
        )
        return False, node["id"]
    node = topology.allocate(rid, actor_id, amount, when)
    return True, node["id"]


def _job_cycle(actors, topology, rng, year, month):
    if month != 10 or year not in (2026, 2027, 2028):
        return []
    _reset_cycle_resources(topology, _when(year, month))
    rows = []
    candidates = [aid for aid in NEW_ACTORS if actors[aid]["stage"] in ("doctoral", "search")]
    candidates.sort(key=lambda aid: (-_score(actors[aid]), aid))
    for actor_id in candidates:
        actor = actors[actor_id]
        ok, node_id = _allocate_target_resource(actor_id, actor, topology, _when(year, month))
        score = _score(actor)
        if not ok:
            actor["history"].append({"date": _when(year, month), "event": "resource_blocked"})
            rows.append({"date": _when(year, month), "actor": actor_id, "outcome": "blocked", "node": node_id})
            continue
        threshold = rng.uniform(.54, .76) + .025 * max(0, year - 2026)
        if score >= threshold:
            actor["stage"] = "employed"
            actor["sector"] = actor["current_target"]
            actor["stability"] = min(1.0, .58 + .20 * score)
            actor["mobility"] = max(.30, actor["mobility"] - .08)
            actor["career_satisfaction"] = min(1.0, .48 + .28 * score + rng.uniform(-.08, .08))
            node = topology._node(
                "first_job_accepted", _when(year, month), actor=actor_id,
                target=actor["sector"], payload={"score": round(score, 4)},
                causes=[node_id],
            )
            outcome = "accepted"
            actor["history"].append({"date": _when(year, month), "event": "first_job_accepted", "sector": actor["sector"]})
        else:
            actor["stage"] = "search"
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .04)
            node = topology._node(
                "job_cycle_failed", _when(year, month), actor=actor_id,
                target=actor["current_target"], payload={"score": round(score, 4)},
                causes=[node_id],
            )
            outcome = "failed"
            actor["history"].append({"date": _when(year, month), "event": "job_cycle_failed"})
        rows.append({"date": _when(year, month), "actor": actor_id, "outcome": outcome, "node": node["id"], "score": round(score, 4)})
    return rows


def _family_pressure(actors, topology, rng, year, month):
    if year < 2030 or month != 6:
        return []
    out = []
    for actor_id in NEW_ACTORS:
        actor = actors[actor_id]
        base = .08 + .025 * (year - 2030)
        volatility = rng.uniform(-.04, .08)
        load = max(0.0, min(.65, (base + volatility) * (0.65 + actor["family_care_share"])))
        actor["family_care_load"] = load
        actor["mobility"] = max(.08, actor["mobility"] - .06 * load)
        node = topology._node(
            "family_care_bargain_updated", _when(year, month), actor=actor_id,
            payload={
                "care_share": round(actor["family_care_share"], 4),
                "care_load": round(load, 4),
                "note": "family structure changes bargaining set, not a predetermined duty",
            },
        )
        out.append({"date": _when(year, month), "actor": actor_id, "care_load": round(load, 4), "node": node["id"]})
    return out


def _career_reassessment(actors, originals, topology, rng, year, month):
    if month != 9 or year not in (2032, 2034):
        return []
    out = []
    for actor_id in NEW_ACTORS:
        actor = actors[actor_id]
        if actor["stage"] != "employed":
            continue
        old_sector = actor["sector"]
        shock = rng.uniform(-.10, .08)
        care_cost = .16 * actor["family_care_load"]
        actor["career_satisfaction"] = max(
            .05, min(1.0, actor["career_satisfaction"] + shock - care_cost)
        )
        changed = False
        if actor["career_satisfaction"] < .34 and actor["mobility"] > .26:
            if old_sector in ("state_owned_enterprise", "civil_service", "university_counselor"):
                actor["current_target"] = "civil_service_or_public_institution" if actor_id != "zhou_ye" else "state_owned_enterprise"
            elif old_sector == "university_faculty":
                actor["current_target"] = "pharmaceutical_industry"
            elif old_sector == "pharmaceutical_industry":
                actor["current_target"] = "university_faculty"
            actor["stage"] = "search"
            changed = True
        node = topology._node(
            "career_reassessment", _when(year, month), actor=actor_id,
            payload={
                "old_sector": old_sector,
                "changed_search_direction": changed,
                "satisfaction": round(actor["career_satisfaction"], 4),
                "mobility": round(actor["mobility"], 4),
            },
        )
        out.append({"date": _when(year, month), "actor": actor_id, "changed": changed, "node": node["id"]})
    originals["lin_jing"]["mobility"] = max(.10, originals["lin_jing"]["mobility"] - .01 * len(out))
    originals["chen_lan"]["network"] = min(1.0, originals["chen_lan"]["network"] + .005 * len(out))
    originals["xu_hang"]["network"] = min(1.0, originals["xu_hang"]["network"] + .005 * len(out))
    return out


def simulate_career_six_world(seed=1, design=None):
    """Run one non-canonical 2026-2035 branch.

    This is a scouting simulator, not a canonical biography. It preserves fixed
    starting constraints and produces auditable interactions with the original
    Beijing characters.
    """
    design = deepcopy(design or load_career_six_design())
    rng = random.Random(seed)
    topology = _topology(design)
    actors, originals = _initial_state(design, rng)
    interactions, job_cycles, family_events, reassessments = [], [], [], []
    snapshots = []

    for year, month in _month_iter():
        for actor_id, actor in actors.items():
            if actor["stage"] in ("doctoral", "search"):
                actor["readiness"]["technical"] = min(1.0, actor["readiness"]["technical"] + .0020)
                actor["readiness"]["exam"] = min(1.0, actor["readiness"]["exam"] + .0015)
                actor["readiness"]["research"] = min(1.0, actor["readiness"]["research"] + .0016)
                actor["readiness"]["translation"] = min(1.0, actor["readiness"]["translation"] + .0014)
            elif actor["stage"] == "employed":
                if actor["sector"] == "university_faculty":
                    actor["readiness"]["research"] = min(1.0, actor["readiness"]["research"] + .0022)
                elif actor["sector"] == "pharmaceutical_industry":
                    actor["readiness"]["translation"] = min(1.0, actor["readiness"]["translation"] + .0024)
                else:
                    actor["readiness"]["translation"] = min(1.0, actor["readiness"]["translation"] + .0012)

        interactions.extend(_apply_interactions(actors, originals, topology, year, month))
        job_cycles.extend(_job_cycle(actors, topology, rng, year, month))
        family_events.extend(_family_pressure(actors, topology, rng, year, month))
        reassessments.extend(_career_reassessment(actors, originals, topology, rng, year, month))

        if month == 10 and year in (2032, 2034):
            _reset_cycle_resources(topology, _when(year, month))
            for actor_id in NEW_ACTORS:
                actor = actors[actor_id]
                if actor["stage"] != "search":
                    continue
                ok, node_id = _allocate_target_resource(actor_id, actor, topology, _when(year, month))
                if not ok:
                    continue
                score = _score(actor) + rng.uniform(-.04, .05)
                if score >= rng.uniform(.60, .78):
                    old = actor["sector"]
                    actor["sector"] = actor["current_target"]
                    actor["stage"] = "employed"
                    actor["career_satisfaction"] = min(1.0, .48 + .25 * score)
                    topology._node(
                        "midcareer_reentry", _when(year, month), actor=actor_id,
                        target=actor["sector"], payload={"from": old, "score": round(score, 4)},
                        causes=[node_id],
                    )

        if month == 12:
            snapshots.append({
                "year": year,
                "actors": deepcopy(actors),
                "original_core": deepcopy(originals),
            })

    return {
        "seed": seed,
        "status": "career_six_2026_2035_noncanonical_scout",
        "start_date": design["start_date"],
        "end_date": design["end_date"],
        "actors": actors,
        "original_core": originals,
        "interactions": interactions,
        "job_cycles": job_cycles,
        "family_events": family_events,
        "reassessments": reassessments,
        "annual_snapshots": snapshots,
        "topology": topology.snapshot(),
        "fixed_design_rules": deepcopy(design["fixed_design_rules"]),
    }
