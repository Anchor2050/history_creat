"""Household + city-bundle pass v3 for the six-character 2026-2035 branch.

This layer keeps the v1/v2 history available for comparison, then makes two
previously compressed objects explicit:

1. family care is produced by concrete parent/sibling nodes rather than one
   exogenous scalar; and
2. winning a career opportunity produces a city-specific employment bundle
   that can still be rejected because wage, housing, commute, welfare,
   family distance, flexibility and re-entry value do not line up.

All numeric bundle values are fictional engineering priors for replay. They are
not claims about a real employer, city or salary distribution.
"""
from copy import deepcopy
import random

from . import career_six_2035 as base
from . import career_six_continuity_v2 as continuity


CITY_BUNDLES = {
    "beijing_core": {
        "wage_multiplier": 1.22,
        "housing_monthly": 6200,
        "commute_hours_daily": 1.45,
        "welfare_continuity": .80,
        "opportunity_density": .96,
        "flexibility": .58,
        "family_distance": 3.6,
    },
    "provincial_capital": {
        "wage_multiplier": 1.00,
        "housing_monthly": 3300,
        "commute_hours_daily": .90,
        "welfare_continuity": .90,
        "opportunity_density": .73,
        "flexibility": .64,
        "family_distance": 1.25,
    },
    "regional_university_city": {
        "wage_multiplier": .88,
        "housing_monthly": 2400,
        "commute_hours_daily": .70,
        "welfare_continuity": .92,
        "opportunity_density": .58,
        "flexibility": .69,
        "family_distance": 1.55,
    },
    "home_prefecture": {
        "wage_multiplier": .78,
        "housing_monthly": 1700,
        "commute_hours_daily": .55,
        "welfare_continuity": .95,
        "opportunity_density": .38,
        "flexibility": .72,
        "family_distance": .20,
    },
    "pharma_cluster": {
        "wage_multiplier": 1.18,
        "housing_monthly": 4600,
        "commute_hours_daily": 1.05,
        "welfare_continuity": .82,
        "opportunity_density": .90,
        "flexibility": .61,
        "family_distance": 3.00,
    },
}

SECTOR_BASE_MONTHLY_GROSS = {
    "state_owned_enterprise": 10500,
    "civil_service": 7200,
    "university_counselor": 7800,
    "university_faculty": 9800,
    "civil_service_or_public_institution": 7600,
    "pharmaceutical_industry": 14500,
}

SECTOR_SECURITY = {
    "state_owned_enterprise": .78,
    "civil_service": .96,
    "university_counselor": .88,
    "university_faculty": .67,
    "civil_service_or_public_institution": .91,
    "pharmaceutical_industry": .56,
}

SECTOR_CITY_OPTIONS = {
    "state_owned_enterprise": ("beijing_core", "provincial_capital", "home_prefecture"),
    "civil_service": ("beijing_core", "provincial_capital", "home_prefecture"),
    "university_counselor": ("beijing_core", "provincial_capital", "regional_university_city"),
    "university_faculty": ("beijing_core", "provincial_capital", "regional_university_city"),
    "civil_service_or_public_institution": ("provincial_capital", "home_prefecture", "regional_university_city"),
    "pharmaceutical_industry": ("beijing_core", "provincial_capital", "pharma_cluster"),
}

ACTOR_OFFER_WEIGHTS = {
    "zhou_ye": {"money": .19, "security": .22, "opportunity": .15, "family": .24, "welfare": .10, "flexibility": .10},
    "gao_yuan": {"money": .14, "security": .27, "opportunity": .13, "family": .20, "welfare": .16, "flexibility": .10},
    "luo_cheng": {"money": .14, "security": .23, "opportunity": .13, "family": .18, "welfare": .14, "flexibility": .18},
    "tang_yu": {"money": .13, "security": .11, "opportunity": .32, "family": .15, "welfare": .09, "flexibility": .20},
    "he_xin": {"money": .13, "security": .27, "opportunity": .13, "family": .22, "welfare": .16, "flexibility": .09},
    "song_nan": {"money": .22, "security": .10, "opportunity": .29, "family": .13, "welfare": .08, "flexibility": .18},
}

ACTOR_ACCEPT_THRESHOLD = {
    "zhou_ye": .50,
    "gao_yuan": .51,
    "luo_cheng": .49,
    "tang_yu": .52,
    "he_xin": .51,
    "song_nan": .50,
}


def _clip(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, value))


def _build_households(design, rng):
    """Create concrete, noncanonical household nodes from fixed family facts."""
    households = {}
    for actor_id, actor in design["actors"].items():
        only_child = bool(actor.get("only_child"))
        mother_age = rng.randint(55, 61)
        father_age = rng.randint(57, 63)
        parents = {
            "mother": {
                "id": f"{actor_id}:mother",
                "age_2026": mother_age,
                "employment_context": "dual_income_fixed" if only_child else "open_scenario",
                "health_need": rng.uniform(.02, .10),
                "retirement_buffer": rng.uniform(.35, .78),
            },
            "father": {
                "id": f"{actor_id}:father",
                "age_2026": father_age,
                "employment_context": "dual_income_fixed" if only_child else "open_scenario",
                "health_need": rng.uniform(.02, .11),
                "retirement_buffer": rng.uniform(.35, .80),
            },
        }
        siblings = []
        if actor.get("older_brothers") == 2:
            for index in (1, 2):
                siblings.append({
                    "id": f"{actor_id}:older_brother_{index}",
                    "age_gap": rng.randint(3 + 3 * (index - 1), 7 + 4 * (index - 1)),
                    "city": rng.choice(("home_prefecture", "provincial_capital", "beijing_core")),
                    "income_capacity": rng.uniform(.35, .88),
                    "care_willingness": rng.uniform(.18, .86),
                    "partner_child_load": rng.uniform(.05, .95),
                    "relationship_quality": rng.uniform(.35, .90),
                })
        households[actor_id] = {
            "actor": actor_id,
            "family_anchor": "home_region",
            "parents": parents,
            "siblings": siblings,
            "home_housing_security": rng.uniform(.42, .90),
            "paid_care_market_access": rng.uniform(.28, .82),
            "care_need": 0.0,
            "sibling_substitution": 0.0,
            "paid_care_substitution": 0.0,
            "actor_care_share": 0.0,
            "unmet_care": 0.0,
            "events": [],
        }
    return households


def _sibling_substitution(profile):
    total = 0.0
    for sibling in profile["siblings"]:
        proximity = {
            "home_prefecture": 1.0,
            "provincial_capital": .72,
            "beijing_core": .42,
        }[sibling["city"]]
        free_capacity = max(0.05, 1.0 - .70 * sibling["partner_child_load"])
        total += (
            sibling["care_willingness"]
            * sibling["relationship_quality"]
            * sibling["income_capacity"]
            * proximity
            * free_capacity
        )
    return min(1.25, total)


def _update_household(actor_id, actor, profile, topology, rng, year, month):
    if month != 6 or year < 2030:
        return None
    shock_nodes = []
    need = 0.0
    for parent in profile["parents"].values():
        age = parent["age_2026"] + (year - 2026)
        age_pressure = max(0.0, age - 60) * .016
        shock_probability = .05 + max(0, age - 61) * .012
        if rng.random() < min(.28, shock_probability):
            shock = rng.uniform(.06, .20)
            parent["health_need"] = min(.85, parent["health_need"] + shock)
            node = topology._node(
                "parent_health_need_increased",
                base._when(year, month),
                actor=actor_id,
                target=parent["id"],
                payload={"increase": round(shock, 4), "age": age},
            )
            shock_nodes.append(node["id"])
        need += min(.90, parent["health_need"] + age_pressure)

    sibling_capacity = _sibling_substitution(profile)
    paid_capacity = (
        profile["paid_care_market_access"]
        * _clip(actor["cash"] / 42000.0)
        * .62
    )
    residual = max(0.0, need - sibling_capacity - paid_capacity)
    actor_share = 0.0 if need <= 1e-9 else min(1.0, residual / need)
    unmet = max(0.0, residual - .72)

    profile["care_need"] = need
    profile["sibling_substitution"] = sibling_capacity
    profile["paid_care_substitution"] = paid_capacity
    profile["actor_care_share"] = actor_share
    profile["unmet_care"] = unmet

    actor["family_care_load"] = _clip(.62 * actor["family_care_load"] + .38 * actor_share * min(1.0, need), 0, .80)
    actor["mobility"] = max(.06, actor["mobility"] - .045 * actor["family_care_load"])

    node = topology._node(
        "household_care_network_rebalanced",
        base._when(year, month),
        actor=actor_id,
        payload={
            "care_need": round(need, 4),
            "sibling_substitution": round(sibling_capacity, 4),
            "paid_care_substitution": round(paid_capacity, 4),
            "actor_care_share": round(actor_share, 4),
            "unmet_care": round(unmet, 4),
        },
        causes=shock_nodes,
    )
    event = {
        "date": base._when(year, month),
        "actor": actor_id,
        "care_need": round(need, 4),
        "sibling_substitution": round(sibling_capacity, 4),
        "paid_care_substitution": round(paid_capacity, 4),
        "actor_care_share": round(actor_share, 4),
        "unmet_care": round(unmet, 4),
        "node": node["id"],
    }
    profile["events"].append(deepcopy(event))
    return event


def _city_weights(actor, cities):
    if actor.get("preferred_city_shift") == "closer_to_family":
        weights = []
        for city in cities:
            distance = CITY_BUNDLES[city]["family_distance"]
            weights.append(max(.15, 2.3 - distance))
        return weights
    return [1.0] * len(cities)


def _generate_offer(actor_id, actor, household, rng, year, phase):
    sector = actor["current_target"]
    cities = SECTOR_CITY_OPTIONS[sector]
    city = rng.choices(cities, weights=_city_weights(actor, cities), k=1)[0]
    city_row = CITY_BUNDLES[city]
    salary = (
        SECTOR_BASE_MONTHLY_GROSS[sector]
        * city_row["wage_multiplier"]
        * rng.uniform(.93, 1.08)
        * (1.0 + .012 * max(0, year - 2026))
    )
    security = _clip(SECTOR_SECURITY[sector] + rng.uniform(-.05, .05))
    flexibility = _clip(city_row["flexibility"] + rng.uniform(-.08, .08))
    if sector == "university_faculty":
        flexibility = _clip(flexibility - .06)
    if sector == "pharmaceutical_industry":
        security = _clip(security - .04)
    return {
        "id": f"offer:{actor_id}:{year}:{phase}:{sector}:{city}",
        "actor": actor_id,
        "year": year,
        "phase": phase,
        "sector": sector,
        "city": city,
        "monthly_gross": round(salary, 2),
        "housing_monthly": city_row["housing_monthly"],
        "commute_hours_daily": city_row["commute_hours_daily"],
        "welfare_continuity": city_row["welfare_continuity"],
        "opportunity_density": city_row["opportunity_density"],
        "family_distance": city_row["family_distance"],
        "contract_security": round(security, 4),
        "flexibility": round(flexibility, 4),
        "relocation_cost": round(city_row["housing_monthly"] * 1.45 + city_row["family_distance"] * 900, 2),
        "engineering_prior": True,
    }


def _evaluate_offer(actor_id, actor, household, offer):
    care_load = actor["family_care_load"]
    distance = offer["family_distance"]
    family_transfer = 1800.0 * care_load * (1.0 + .16 * distance)
    commute_cost = 520.0 * offer["commute_hours_daily"]
    disposable = offer["monthly_gross"] - offer["housing_monthly"] - commute_cost - family_transfer
    money = _clip((disposable - 500.0) / 8500.0)
    family = _clip(
        1.0
        - .34 * care_load * distance
        - .55 * household["unmet_care"]
        + .12 * household["sibling_substitution"]
    )
    opportunity = offer["opportunity_density"]
    welfare = offer["welfare_continuity"]
    security = offer["contract_security"]
    flexibility = offer["flexibility"]
    weights = ACTOR_OFFER_WEIGHTS[actor_id]
    score = (
        weights["money"] * money
        + weights["security"] * security
        + weights["opportunity"] * opportunity
        + weights["family"] * family
        + weights["welfare"] * welfare
        + weights["flexibility"] * flexibility
    )
    hard_family_block = (
        household["unmet_care"] > .38
        and care_load > .42
        and distance > 2.4
    )
    hard_cash_block = disposable < 0
    accepted = (
        score >= ACTOR_ACCEPT_THRESHOLD[actor_id]
        and not hard_family_block
        and not hard_cash_block
    )
    return {
        "accepted": accepted,
        "score": round(score, 4),
        "threshold": ACTOR_ACCEPT_THRESHOLD[actor_id],
        "money": round(money, 4),
        "family_feasibility": round(family, 4),
        "disposable_after_bundle": round(disposable, 2),
        "hard_family_block": hard_family_block,
        "hard_cash_block": hard_cash_block,
    }


def _maybe_revise_target_v3(actor_id, actor, topology, rng, year, month, cause_node):
    pressure = (
        actor["failed_cycles"]
        + actor["blocked_cycles"]
        + actor.get("bundle_rejections", 0)
    )
    if year < 2028 or pressure < 2 or actor["target_revision_count"] >= 2:
        return None
    if rng.random() >= .60:
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
    actor["bundle_rejections"] = 0
    node = topology._node(
        "career_target_revised_after_search_and_bundle_pressure",
        base._when(year, month),
        actor=actor_id,
        target=actor["current_target"],
        payload={"from": old, "to": actor["current_target"]},
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


def _accept_offer(actor_id, actor, offer, evaluation, originals, topology, when, resource_node, phase):
    old_sector = actor.get("sector")
    actor.update(
        stage="employed",
        sector=offer["sector"],
        city_state=offer["city"],
        employment_terms=deepcopy(offer),
        failed_cycles=0,
        blocked_cycles=0,
        bundle_rejections=0,
        preferred_city_shift=None,
    )
    actor["stability"] = _clip(.45 + .38 * offer["contract_security"])
    actor["mobility"] = max(.14, actor["mobility"] - .05 * offer["contract_security"])
    actor["career_satisfaction"] = _clip(.43 + .32 * evaluation["score"])
    kind = "first_job_bundle_accepted" if phase == "first_job" else "midcareer_bundle_accepted"
    node = topology._node(
        kind,
        when,
        actor=actor_id,
        target=f"{offer['sector']}@{offer['city']}",
        payload={
            "from_sector": old_sector,
            "offer_id": offer["id"],
            "bundle_score": evaluation["score"],
        },
        causes=[resource_node],
    )
    continuity._backprop_accepted_job(
        actor_id, actor, originals, topology, when, node["id"]
    )
    actor["history"].append({
        "date": when,
        "event": kind,
        "sector": offer["sector"],
        "city": offer["city"],
        "node": node["id"],
    })
    return node["id"]


def _job_cycle(actors, households, originals, topology, rng, year, month, offers):
    if month != 10 or year not in continuity.JOB_CYCLE_YEARS:
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
        ok, resource_node, holders = continuity._allocate(
            actor_id, actor, topology, base._when(year, month)
        )
        score = base._score(actor)
        if not ok:
            actor["stage"] = "search"
            actor["blocked_cycles"] += 1
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .02)
            _maybe_revise_target_v3(actor_id, actor, topology, rng, year, month, resource_node)
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "capacity_blocked", "holders": holders, "node": resource_node,
            })
            continue

        qualification_threshold = rng.uniform(.62, .84) + .010 * max(0, year - 2026)
        if score < qualification_threshold:
            actor["stage"] = "search"
            actor["failed_cycles"] += 1
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .04)
            node = topology._node(
                "job_cycle_failed_before_offer",
                base._when(year, month),
                actor=actor_id,
                target=actor["current_target"],
                payload={"score": round(score, 4), "threshold": round(qualification_threshold, 4)},
                causes=[resource_node],
            )
            _maybe_revise_target_v3(actor_id, actor, topology, rng, year, month, node["id"])
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "qualification_failed", "node": node["id"],
            })
            continue

        offer = _generate_offer(actor_id, actor, households[actor_id], rng, year, "first_job")
        evaluation = _evaluate_offer(actor_id, actor, households[actor_id], offer)
        offers.append({**deepcopy(offer), "evaluation": deepcopy(evaluation)})
        offer_node = topology._node(
            "city_specific_job_offer_received",
            base._when(year, month),
            actor=actor_id,
            target=f"{offer['sector']}@{offer['city']}",
            payload={"offer_id": offer["id"], "evaluation": evaluation},
            causes=[resource_node],
        )
        if evaluation["accepted"]:
            accepted_node = _accept_offer(
                actor_id, actor, offer, evaluation, originals, topology,
                base._when(year, month), offer_node["id"], "first_job"
            )
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "offer_accepted", "city": offer["city"],
                "sector": offer["sector"], "node": accepted_node,
            })
        else:
            actor["stage"] = "search"
            actor["bundle_rejections"] += 1
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .025)
            reject_node = topology._node(
                "job_offer_rejected_due_to_bundle",
                base._when(year, month),
                actor=actor_id,
                target=offer["id"],
                payload={"evaluation": evaluation},
                causes=[offer_node["id"]],
            )
            _maybe_revise_target_v3(actor_id, actor, topology, rng, year, month, reject_node["id"])
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "offer_rejected", "city": offer["city"],
                "sector": offer["sector"], "node": reject_node["id"],
            })
    return rows


def _reassess(actors, households, topology, rng, year, month):
    if month != 9 or year not in (2032, 2034):
        return []
    rows = []
    for actor_id, actor in actors.items():
        if actor["stage"] != "employed" or not actor.get("employment_terms"):
            continue
        offer = actor["employment_terms"]
        family_drag = actor["family_care_load"] * offer["family_distance"]
        actor["career_satisfaction"] = _clip(
            actor["career_satisfaction"]
            + rng.uniform(-.09, .07)
            - .075 * family_drag
            - .055 * households[actor_id]["unmet_care"]
        )
        changed = False
        reason = "stay"
        if family_drag > .72 and actor["mobility"] > .20:
            actor["stage"] = "search"
            actor["preferred_city_shift"] = "closer_to_family"
            changed = True
            reason = "family_distance_repricing"
        elif actor["career_satisfaction"] < .34 and actor["mobility"] > .24:
            actor["stage"] = "search"
            options = [x for x in base.FALLBACK_TARGETS[actor_id] if x != actor["current_target"]]
            if options and rng.random() < .68:
                actor["current_target"] = rng.choice(options)
            changed = True
            reason = "career_satisfaction_repricing"
        node = topology._node(
            "city_household_career_reassessment",
            base._when(year, month),
            actor=actor_id,
            payload={
                "changed": changed,
                "reason": reason,
                "satisfaction": round(actor["career_satisfaction"], 4),
                "family_drag": round(family_drag, 4),
            },
        )
        rows.append({
            "date": base._when(year, month), "actor": actor_id,
            "changed": changed, "reason": reason, "node": node["id"],
        })
    return rows


def _reentry(actors, households, originals, topology, rng, year, month, offers):
    if month != 10 or year not in (2032, 2034):
        return []
    base._reset(topology, base._when(year, month))
    rows = []
    for actor_id, actor in actors.items():
        if actor["stage"] != "search":
            continue
        ok, resource_node, holders = continuity._allocate(
            actor_id, actor, topology, base._when(year, month)
        )
        if not ok:
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "capacity_blocked", "holders": holders, "node": resource_node,
            })
            continue
        score = base._score(actor) + rng.uniform(-.04, .05)
        if score < rng.uniform(.60, .80):
            actor["failed_cycles"] += 1
            node = topology._node(
                "midcareer_search_failed_before_offer",
                base._when(year, month),
                actor=actor_id,
                target=actor["current_target"],
                payload={"score": round(score, 4)},
                causes=[resource_node],
            )
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "qualification_failed", "node": node["id"],
            })
            continue
        offer = _generate_offer(actor_id, actor, households[actor_id], rng, year, "reentry")
        evaluation = _evaluate_offer(actor_id, actor, households[actor_id], offer)
        offers.append({**deepcopy(offer), "evaluation": deepcopy(evaluation)})
        offer_node = topology._node(
            "city_specific_reentry_offer_received",
            base._when(year, month),
            actor=actor_id,
            target=f"{offer['sector']}@{offer['city']}",
            payload={"offer_id": offer["id"], "evaluation": evaluation},
            causes=[resource_node],
        )
        if evaluation["accepted"]:
            accepted_node = _accept_offer(
                actor_id, actor, offer, evaluation, originals, topology,
                base._when(year, month), offer_node["id"], "reentry"
            )
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "offer_accepted", "city": offer["city"],
                "sector": offer["sector"], "node": accepted_node,
            })
        else:
            actor["bundle_rejections"] += 1
            reject_node = topology._node(
                "reentry_offer_rejected_due_to_bundle",
                base._when(year, month),
                actor=actor_id,
                target=offer["id"],
                payload={"evaluation": evaluation},
                causes=[offer_node["id"]],
            )
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "offer_rejected", "city": offer["city"],
                "sector": offer["sector"], "node": reject_node["id"],
            })
    return rows


def simulate_career_six_household_city(seed=1, design=None):
    """Run the v3 household/city-bundle noncanonical scout."""
    design = deepcopy(design or base.load_career_six_design())
    rng = random.Random(seed)
    topology = continuity._topology(design)
    actors, originals = continuity._initial_state(design, rng)
    households = _build_households(design, rng)
    for actor in actors.values():
        actor["bundle_rejections"] = 0
        actor["preferred_city_shift"] = None
        actor["employment_terms"] = None

    interactions, jobs, family, reassessments, reentries, offers, snapshots = [], [], [], [], [], [], []

    for year, month in base._months():
        for actor in actors.values():
            if actor["stage"] in ("doctoral", "search"):
                for key, delta in (
                    ("technical", .0020), ("exam", .0015),
                    ("research", .0016), ("translation", .0014),
                ):
                    actor["readiness"][key] = min(1.0, actor["readiness"][key] + delta)
            elif actor["sector"] == "university_faculty":
                actor["readiness"]["research"] = min(1.0, actor["readiness"]["research"] + .0022)
            elif actor["sector"] == "pharmaceutical_industry":
                actor["readiness"]["translation"] = min(1.0, actor["readiness"]["translation"] + .0024)
            else:
                actor["readiness"]["translation"] = min(1.0, actor["readiness"]["translation"] + .0012)

        interactions.extend(continuity._interactions(actors, originals, topology, year, month))

        for actor_id in base.NEW_ACTORS:
            event = _update_household(
                actor_id, actors[actor_id], households[actor_id], topology, rng, year, month
            )
            if event:
                family.append(event)

        reassessments.extend(_reassess(actors, households, topology, rng, year, month))
        jobs.extend(_job_cycle(actors, households, originals, topology, rng, year, month, offers))
        reentries.extend(_reentry(actors, households, originals, topology, rng, year, month, offers))

        if month == 12:
            snapshots.append({
                "year": year,
                "actors": deepcopy(actors),
                "households": deepcopy(households),
                "original_core": deepcopy(originals),
            })

    return {
        "seed": seed,
        "status": "career_six_2026_2035_household_city_v3_noncanonical_scout",
        "start_date": design["start_date"],
        "end_date": design["end_date"],
        "actors": actors,
        "households": households,
        "original_core": originals,
        "interactions": interactions,
        "job_cycles": jobs,
        "family_events": family,
        "reassessments": reassessments,
        "reentries": reentries,
        "offers": offers,
        "capacity_conflicts": [x for x in jobs + reentries if x.get("outcome") == "capacity_blocked"],
        "offer_rejections": [x for x in jobs + reentries if x.get("outcome") == "offer_rejected"],
        "annual_snapshots": snapshots,
        "topology": topology.snapshot(),
        "fixed_design_rules": deepcopy(design["fixed_design_rules"]),
        "engineering_prior_notice": "City, wage, housing, commute, welfare and household parameters in v3 are fictional replay priors, not empirical estimates.",
    }
