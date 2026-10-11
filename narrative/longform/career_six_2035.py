"""Non-canonical 2026-2035 career-world extension for six doctoral characters."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import random

from .consequence_topology import ConsequenceTopology, DEFAULT_TOPOLOGY

NEW_ACTORS = ("zhou_ye", "gao_yuan", "luo_cheng", "tang_yu", "he_xin", "song_nan")
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
TARGET_WEIGHTS = {
    "state_owned_enterprise": {"technical": .45, "translation": .25, "exam": .15, "research": .15},
    "civil_service": {"exam": .55, "translation": .20, "technical": .15, "research": .10},
    "university_counselor": {"translation": .45, "exam": .25, "technical": .15, "research": .15},
    "university_faculty": {"research": .55, "technical": .25, "translation": .15, "exam": .05},
    "civil_service_or_public_institution": {"exam": .45, "translation": .30, "technical": .15, "research": .10},
    "pharmaceutical_industry": {"technical": .30, "translation": .35, "research": .30, "exam": .05},
}
BASE_READINESS = {
    "zhou_ye": {"technical": .68, "exam": .30, "research": .34, "translation": .38},
    "gao_yuan": {"technical": .60, "exam": .58, "research": .30, "translation": .35},
    "luo_cheng": {"technical": .55, "exam": .48, "research": .28, "translation": .52},
    "tang_yu": {"technical": .66, "exam": .32, "research": .62, "translation": .44},
    "he_xin": {"technical": .62, "exam": .56, "research": .50, "translation": .43},
    "song_nan": {"technical": .67, "exam": .30, "research": .52, "translation": .62},
}
FALLBACK_TARGETS = {
    "zhou_ye": ("civil_service_or_public_institution", "university_counselor"),
    "gao_yuan": ("state_owned_enterprise", "university_counselor"),
    "luo_cheng": ("civil_service_or_public_institution", "state_owned_enterprise"),
    "tang_yu": ("pharmaceutical_industry",),
    "he_xin": ("university_counselor", "pharmaceutical_industry"),
    "song_nan": ("university_faculty", "state_owned_enterprise"),
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


def _months():
    y, m = 2026, 3
    while (y, m) <= (2035, 12):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def _when(y, m):
    return date(y, m, 1).isoformat()


def load_career_six_design(path=None):
    path = path or (Path(__file__).resolve().parents[2] / "docs" / "scenarios" / "career-six-2026-2035-v1.json")
    with open(path, encoding="utf-8") as handle:
        design = json.load(handle)
    if design.get("spec_version") != 1 or tuple(design.get("actors", {})) != NEW_ACTORS:
        raise ValueError("invalid career-six scenario")
    return design


def _topology(design):
    state = deepcopy(DEFAULT_TOPOLOGY)
    for aid, actor in design["actors"].items():
        state["actor_status"][aid] = {"active": True, "institution": actor["organization"]}
    state["resources"].update({
        "career.public_sector_mock_interview": {"capacity": 2.0, "allocations": {}},
        "career.university_faculty_referral": {"capacity": 1.0, "allocations": {}},
        "career.university_counselor_referral": {"capacity": 1.0, "allocations": {}},
        "career.state_owned_enterprise_referral": {"capacity": 1.0, "allocations": {}},
        "career.pharma_statistics_project_hours": {"capacity": 40.0, "allocations": {}},
    })
    return ConsequenceTopology(state)


def _initial_state(design, rng):
    actors = {}
    for aid, row in design["actors"].items():
        share = rng.uniform(.72, .98) if row.get("only_child") else rng.uniform(.22, .68)
        actors[aid] = {
            "id": aid, "name": row["name"], "field": row["field"],
            "target_2026": row["career_target_2026"], "current_target": row["career_target_2026"],
            "stage": "doctoral", "sector": None, "city_state": "beijing_training",
            "cash": float(row["cash"]), "readiness": deepcopy(BASE_READINESS[aid]),
            "network": .30, "stability": .20, "mobility": .78,
            "family_care_share": share, "family_care_load": 0.0,
            "career_satisfaction": .50, "failed_cycles": 0,
            "publication_count_fixed": row.get("published_papers"), "history": [],
        }
    originals = {
        "lin_jing": {"public_sector_option": .20, "network": .45, "mobility": .74},
        "chen_lan": {"health_data_translation": .20, "network": .50, "mobility": .62},
        "xu_hang": {"verification_reputation": .42, "network": .38, "mobility": .70},
    }
    return actors, originals


def _reset(topology, when):
    for rid in TARGET_RESOURCE.values():
        row = topology.state["resources"][rid]
        for aid, amount in list(row["allocations"].items()):
            topology.release(rid, aid, amount, when)


def _interactions(actors, originals, topology, y, m):
    active_months = (3, 9) if y <= 2029 else (9,)
    if m not in active_months:
        return []
    rows = []
    for new, old, dim, delta, domain in INTERACTION_RULES:
        actor = actors[new]
        actor["readiness"][dim] = min(1.0, actor["readiness"][dim] + delta)
        actor["network"] = min(1.0, actor["network"] + .012)
        if old in originals:
            if old == "lin_jing":
                originals[old]["public_sector_option"] = min(1.0, originals[old]["public_sector_option"] + .012)
            elif old == "chen_lan":
                originals[old]["health_data_translation"] = min(1.0, originals[old]["health_data_translation"] + .012)
            else:
                originals[old]["verification_reputation"] = min(1.0, originals[old]["verification_reputation"] + .012)
            originals[old]["network"] = min(1.0, originals[old]["network"] + .006)
        node = topology.update_reputation(old, new, domain, .025, _when(y, m))
        rows.append({"date": _when(y, m), "new_actor": new, "existing_actor": old, "domain": domain, "node": node["id"]})
    return rows


def _score(actor):
    weights = TARGET_WEIGHTS[actor["current_target"]]
    return sum(actor["readiness"][k] * w for k, w in weights.items()) + .12 * actor["network"]


def _allocate(aid, actor, topology, when):
    rid = TARGET_RESOURCE[actor["current_target"]]
    amount = 8.0 if rid.endswith("project_hours") else 1.0
    if topology.resource_available(rid) + 1e-12 < amount:
        node = topology._node("career_option_blocked_by_shared_capacity", when, actor=aid, target=rid)
        return False, node["id"]
    node = topology.allocate(rid, aid, amount, when)
    return True, node["id"]


def _job_cycle(actors, topology, rng, y, m):
    if m != 10 or y not in (2026, 2027, 2028):
        return []
    _reset(topology, _when(y, m))
    rows = []
    candidates = [aid for aid in NEW_ACTORS if actors[aid]["stage"] in ("doctoral", "search")]
    candidates.sort(key=lambda aid: (-_score(actors[aid]), aid))
    for aid in candidates:
        actor = actors[aid]
        ok, resource_node = _allocate(aid, actor, topology, _when(y, m))
        score = _score(actor)
        if not ok:
            rows.append({"date": _when(y, m), "actor": aid, "outcome": "blocked", "node": resource_node})
            continue
        threshold = rng.uniform(.62, .84) + .015 * max(0, y - 2026)
        if score >= threshold:
            actor.update(stage="employed", sector=actor["current_target"], failed_cycles=0)
            actor["stability"] = min(1.0, .58 + .20 * score)
            actor["mobility"] = max(.30, actor["mobility"] - .08)
            actor["career_satisfaction"] = min(1.0, .48 + .28 * score + rng.uniform(-.08, .08))
            node = topology._node("first_job_accepted", _when(y, m), actor=aid, target=actor["sector"],
                                  payload={"score": round(score, 4)}, causes=[resource_node])
            outcome = "accepted"
        else:
            actor["stage"] = "search"
            actor["failed_cycles"] += 1
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .04)
            node = topology._node("job_cycle_failed", _when(y, m), actor=aid, target=actor["current_target"],
                                  payload={"score": round(score, 4), "failed_cycles": actor["failed_cycles"]},
                                  causes=[resource_node])
            outcome = "failed"
            if y == 2028 and actor["failed_cycles"] >= 2 and rng.random() < .72:
                old = actor["current_target"]
                actor["current_target"] = rng.choice(FALLBACK_TARGETS[aid])
                revision = topology._node("career_target_revised_after_repeated_failure", _when(y, m),
                                          actor=aid, target=actor["current_target"],
                                          payload={"from": old, "to": actor["current_target"]},
                                          causes=[node["id"]])
                actor["history"].append({"date": _when(y, m), "event": "career_target_revised",
                                         "from": old, "to": actor["current_target"], "node": revision["id"]})
        actor["history"].append({"date": _when(y, m), "event": outcome, "target": actor["current_target"]})
        rows.append({"date": _when(y, m), "actor": aid, "outcome": outcome, "node": node["id"], "score": round(score, 4)})
    return rows


def _family_pressure(actors, topology, rng, y, m):
    if y < 2030 or m != 6:
        return []
    rows = []
    for aid, actor in actors.items():
        base = .08 + .025 * (y - 2030)
        load = max(0.0, min(.65, (base + rng.uniform(-.04, .08)) * (.65 + actor["family_care_share"])))
        actor["family_care_load"] = load
        actor["mobility"] = max(.08, actor["mobility"] - .06 * load)
        node = topology._node("family_care_bargain_updated", _when(y, m), actor=aid,
                              payload={"care_share": round(actor["family_care_share"], 4),
                                       "care_load": round(load, 4),
                                       "note": "family structure changes bargaining set, not predetermined duty"})
        rows.append({"date": _when(y, m), "actor": aid, "care_load": round(load, 4), "node": node["id"]})
    return rows


def _reassess(actors, originals, topology, rng, y, m):
    if m != 9 or y not in (2032, 2034):
        return []
    rows = []
    for aid, actor in actors.items():
        if actor["stage"] != "employed":
            continue
        old = actor["sector"]
        actor["career_satisfaction"] = max(.05, min(1.0,
            actor["career_satisfaction"] + rng.uniform(-.10, .08) - .16 * actor["family_care_load"]))
        changed = False
        if actor["career_satisfaction"] < .34 and actor["mobility"] > .26:
            actor["current_target"] = rng.choice(FALLBACK_TARGETS[aid])
            actor["stage"] = "search"
            changed = True
        node = topology._node("career_reassessment", _when(y, m), actor=aid,
                              payload={"old_sector": old, "changed_search_direction": changed,
                                       "satisfaction": round(actor["career_satisfaction"], 4),
                                       "mobility": round(actor["mobility"], 4)})
        rows.append({"date": _when(y, m), "actor": aid, "changed": changed, "node": node["id"]})
    originals["lin_jing"]["mobility"] = max(.10, originals["lin_jing"]["mobility"] - .01 * len(rows))
    originals["chen_lan"]["network"] = min(1.0, originals["chen_lan"]["network"] + .005 * len(rows))
    originals["xu_hang"]["network"] = min(1.0, originals["xu_hang"]["network"] + .005 * len(rows))
    return rows


def _reentry(actors, topology, rng, y, m):
    if m != 10 or y not in (2032, 2034):
        return
    _reset(topology, _when(y, m))
    for aid, actor in actors.items():
        if actor["stage"] != "search":
            continue
        ok, resource_node = _allocate(aid, actor, topology, _when(y, m))
        if not ok:
            continue
        score = _score(actor) + rng.uniform(-.04, .05)
        if score >= rng.uniform(.62, .82):
            old = actor["sector"]
            actor.update(stage="employed", sector=actor["current_target"], failed_cycles=0)
            actor["career_satisfaction"] = min(1.0, .48 + .25 * score)
            topology._node("midcareer_reentry", _when(y, m), actor=aid, target=actor["sector"],
                           payload={"from": old, "score": round(score, 4)}, causes=[resource_node])


def simulate_career_six_world(seed=1, design=None):
    """Run one auditable, seeded, non-canonical branch from 2026 through 2035."""
    design = deepcopy(design or load_career_six_design())
    rng = random.Random(seed)
    topology = _topology(design)
    actors, originals = _initial_state(design, rng)
    interactions, jobs, family, reassessments, snapshots = [], [], [], [], []

    for y, m in _months():
        for actor in actors.values():
            if actor["stage"] in ("doctoral", "search"):
                for key, delta in (("technical", .0020), ("exam", .0015), ("research", .0016), ("translation", .0014)):
                    actor["readiness"][key] = min(1.0, actor["readiness"][key] + delta)
            elif actor["sector"] == "university_faculty":
                actor["readiness"]["research"] = min(1.0, actor["readiness"]["research"] + .0022)
            elif actor["sector"] == "pharmaceutical_industry":
                actor["readiness"]["translation"] = min(1.0, actor["readiness"]["translation"] + .0024)
            else:
                actor["readiness"]["translation"] = min(1.0, actor["readiness"]["translation"] + .0012)

        interactions.extend(_interactions(actors, originals, topology, y, m))
        jobs.extend(_job_cycle(actors, topology, rng, y, m))
        family.extend(_family_pressure(actors, topology, rng, y, m))
        reassessments.extend(_reassess(actors, originals, topology, rng, y, m))
        _reentry(actors, topology, rng, y, m)

        if m == 12:
            snapshots.append({"year": y, "actors": deepcopy(actors), "original_core": deepcopy(originals)})

    return {
        "seed": seed, "status": "career_six_2026_2035_noncanonical_scout",
        "start_date": design["start_date"], "end_date": design["end_date"],
        "actors": actors, "original_core": originals, "interactions": interactions,
        "job_cycles": jobs, "family_events": family, "reassessments": reassessments,
        "annual_snapshots": snapshots, "topology": topology.snapshot(),
        "fixed_design_rules": deepcopy(design["fixed_design_rules"]),
    }
