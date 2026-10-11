"""Finance + housing pass v4 for the six-character 2026-2035 branch.

V4 closes a missing loop from v3:

salary -> housing/living/care costs -> cash buffer -> paid-care capacity ->
mobility and offer feasibility -> later salary and housing lock-in.

The existing double-entry Ledger is used so cash cannot become negative or be
silently manufactured. Numeric wages/costs remain fictional engineering priors.
"""
from copy import deepcopy
import random

from . import career_six_2035 as base
from . import career_six_continuity_v2 as continuity
from . import career_six_household_city_v3 as v3
from .ledger import Ledger


CITY_LIVING_MONTHLY = {
    "beijing_training": 2300,
    "beijing_core": 3200,
    "provincial_capital": 2500,
    "regional_university_city": 2200,
    "home_prefecture": 1800,
    "pharma_cluster": 2900,
}

NET_PAY_SHARE = .82
TRAINING_HOUSING_MONTHLY = 1500
HOME_BUY_YEARS = (2031, 2033, 2035)


def _ledger_when(year, month):
    if year == 2026 and month == 3:
        return "2026-03-02"
    return base._when(year, month)


def _finance_ledger(design):
    accounts = {actor_id: int(row["cash"]) for actor_id, row in design["actors"].items()}
    accounts.update({
        "external:salary_pool": 100_000_000,
        "external:living_sink": 0,
        "external:housing_sink": 0,
        "external:care_sink": 0,
        "external:relocation_sink": 0,
    })
    weekly = {actor_id: int(row["weekly_discretionary_work_hours"]) for actor_id, row in design["actors"].items()}
    return Ledger("2026-03-02", accounts, weekly)


def _initial_housing():
    return {
        actor_id: {
            "tenure": "rent",
            "work_city": "beijing_training",
            "property_city": None,
            "rent_city": "beijing_training",
            "monthly_rent": TRAINING_HOUSING_MONTHLY,
            "monthly_mortgage": 0,
            "owned_equity": 0,
            "lock_in": 0.0,
            "secondary_rent": 0,
            "purchase_year": None,
            "history": [],
        }
        for actor_id in base.NEW_ACTORS
    }


def _transfer_up_to(ledger, operation_id, source, target, requested, reason):
    requested = max(0, int(round(requested)))
    if requested == 0:
        return {"paid": 0, "unmet": 0}
    available = ledger.state["accounts"][source]
    paid = min(available, requested)
    if paid:
        ledger.transfer(operation_id, source, target, paid, reason)
    return {"paid": paid, "unmet": requested - paid}


def _housing_monthly_cost(housing):
    return housing["monthly_rent"] + housing["monthly_mortgage"] + housing["secondary_rent"]


def _advance_personal_finance(
    actors, households, housing, ledger, topology, year, month
):
    when = _ledger_when(year, month)
    ledger.advance(when)
    rows = []
    for actor_id in base.NEW_ACTORS:
        actor = actors[actor_id]
        house = housing[actor_id]
        salary = 0
        if actor["stage"] == "employed" and actor.get("employment_terms"):
            salary = int(round(actor["employment_terms"]["monthly_gross"] * NET_PAY_SHARE))
            ledger.transfer(
                f"salary:{actor_id}:{year:04d}-{month:02d}",
                "external:salary_pool",
                actor_id,
                salary,
                "monthly net-pay engineering prior",
            )

        living_requested = CITY_LIVING_MONTHLY.get(house["work_city"], 2400)
        housing_requested = _housing_monthly_cost(house)
        care_requested = int(round(
            2300
            * actor["family_care_load"]
            * (1.0 + .35 * households[actor_id]["unmet_care"])
        ))

        living = _transfer_up_to(
            ledger,
            f"living:{actor_id}:{year:04d}-{month:02d}",
            actor_id,
            "external:living_sink",
            living_requested,
            "monthly living costs",
        )
        housing_paid = _transfer_up_to(
            ledger,
            f"housing:{actor_id}:{year:04d}-{month:02d}",
            actor_id,
            "external:housing_sink",
            housing_requested,
            "rent/mortgage/secondary housing costs",
        )
        care = _transfer_up_to(
            ledger,
            f"care:{actor_id}:{year:04d}-{month:02d}",
            actor_id,
            "external:care_sink",
            care_requested,
            "paid elder-care contribution",
        )

        if house["tenure"] == "owned_mortgage" and house["monthly_mortgage"]:
            principal = int(round(house["monthly_mortgage"] * .18))
            house["owned_equity"] += min(principal, housing_paid["paid"])

        unmet = living["unmet"] + housing_paid["unmet"] + care["unmet"]
        actor["cash"] = float(ledger.state["accounts"][actor_id])
        if unmet:
            actor["career_satisfaction"] = max(.05, actor["career_satisfaction"] - .012)
            actor["mobility"] = max(.05, actor["mobility"] - .008)
            node = topology._node(
                "monthly_expense_unmet",
                when,
                actor=actor_id,
                payload={
                    "unmet": unmet,
                    "living_unmet": living["unmet"],
                    "housing_unmet": housing_paid["unmet"],
                    "care_unmet": care["unmet"],
                },
            )
            unmet_node = node["id"]
        else:
            unmet_node = None

        rows.append({
            "date": when,
            "actor": actor_id,
            "salary": salary,
            "living_paid": living["paid"],
            "housing_paid": housing_paid["paid"],
            "care_paid": care["paid"],
            "unmet": unmet,
            "cash_after": ledger.state["accounts"][actor_id],
            "node": unmet_node,
        })
    return rows


def _move_housing_after_job(actor_id, housing, offer, topology, when, cause_node):
    house = housing[actor_id]
    old_work_city = house["work_city"]
    new_city = offer["city"]
    house["work_city"] = new_city
    if house["tenure"] == "rent":
        house["rent_city"] = new_city
        house["monthly_rent"] = int(round(offer["housing_monthly"]))
        house["secondary_rent"] = 0
    elif house["property_city"] == new_city:
        house["rent_city"] = None
        house["monthly_rent"] = 0
        house["secondary_rent"] = 0
    else:
        house["rent_city"] = new_city
        house["monthly_rent"] = 0
        house["secondary_rent"] = int(round(offer["housing_monthly"]))

    node = topology._node(
        "housing_state_changed_after_job",
        when,
        actor=actor_id,
        target=new_city,
        payload={
            "from_work_city": old_work_city,
            "tenure": house["tenure"],
            "property_city": house["property_city"],
            "monthly_housing_cost": _housing_monthly_cost(house),
        },
        causes=[cause_node],
    )
    house["history"].append({
        "date": when,
        "event": "work_city_changed",
        "from": old_work_city,
        "to": new_city,
        "node": node["id"],
    })
    return node["id"]


def _evaluate_offer_v4(actor_id, actor, household, housing, offer):
    evaluation = v3._evaluate_offer(actor_id, actor, household, offer)
    house = housing[actor_id]
    carry_cost = 0
    lock_penalty = 0.0
    same_property_city_bonus = 0.0
    if house["tenure"] == "owned_mortgage":
        if house["property_city"] != offer["city"]:
            carry_cost = house["monthly_mortgage"]
            lock_penalty = .16 * house["lock_in"]
        else:
            same_property_city_bonus = .05 * house["lock_in"]

    adjusted_disposable = evaluation["disposable_after_bundle"] - carry_cost
    adjusted_score = v3._clip(evaluation["score"] - lock_penalty + same_property_city_bonus)
    hard_housing_block = adjusted_disposable < -500
    accepted = (
        adjusted_score >= v3.ACTOR_ACCEPT_THRESHOLD[actor_id]
        and not evaluation["hard_family_block"]
        and not evaluation["hard_cash_block"]
        and not hard_housing_block
    )
    return {
        **evaluation,
        "accepted": accepted,
        "score": round(adjusted_score, 4),
        "pre_housing_lock_score": evaluation["score"],
        "carry_cost_from_existing_property": carry_cost,
        "lock_penalty": round(lock_penalty, 4),
        "same_property_city_bonus": round(same_property_city_bonus, 4),
        "disposable_after_existing_property": round(adjusted_disposable, 2),
        "hard_housing_block": hard_housing_block,
    }


def _accept_offer_v4(
    actor_id, actor, offer, evaluation, originals, housing, topology, when,
    resource_node, phase
):
    accepted = v3._accept_offer(
        actor_id, actor, offer, evaluation, originals, topology, when,
        resource_node, phase
    )
    _move_housing_after_job(actor_id, housing, offer, topology, when, accepted)
    return accepted


def _job_cycle(
    actors, households, housing, originals, topology, rng, year, month, offers
):
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
            v3._maybe_revise_target_v3(actor_id, actor, topology, rng, year, month, resource_node)
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "capacity_blocked", "holders": holders, "node": resource_node,
            })
            continue

        threshold = rng.uniform(.62, .84) + .010 * max(0, year - 2026)
        if score < threshold:
            actor["stage"] = "search"
            actor["failed_cycles"] += 1
            node = topology._node(
                "job_cycle_failed_before_offer",
                base._when(year, month),
                actor=actor_id,
                target=actor["current_target"],
                payload={"score": round(score, 4), "threshold": round(threshold, 4)},
                causes=[resource_node],
            )
            v3._maybe_revise_target_v3(actor_id, actor, topology, rng, year, month, node["id"])
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "qualification_failed", "node": node["id"],
            })
            continue

        offer = v3._generate_offer(
            actor_id, actor, households[actor_id], rng, year, "first_job"
        )
        evaluation = _evaluate_offer_v4(
            actor_id, actor, households[actor_id], housing, offer
        )
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
            accepted_node = _accept_offer_v4(
                actor_id, actor, offer, evaluation, originals, housing, topology,
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
            reject_node = topology._node(
                "job_offer_rejected_after_finance_housing_check",
                base._when(year, month),
                actor=actor_id,
                target=offer["id"],
                payload={"evaluation": evaluation},
                causes=[offer_node["id"]],
            )
            v3._maybe_revise_target_v3(actor_id, actor, topology, rng, year, month, reject_node["id"])
            rows.append({
                "date": base._when(year, month), "actor": actor_id,
                "outcome": "offer_rejected", "city": offer["city"],
                "sector": offer["sector"], "node": reject_node["id"],
            })
    return rows


def _reassess(actors, households, housing, topology, rng, year, month):
    rows = v3._reassess(actors, households, topology, rng, year, month)
    if not rows:
        return rows
    for row in rows:
        if not row["changed"]:
            continue
        actor_id = row["actor"]
        house = housing[actor_id]
        if house["tenure"] == "owned_mortgage":
            topology._node(
                "career_reassessment_carries_housing_lock_in",
                base._when(year, month),
                actor=actor_id,
                target=house["property_city"],
                payload={
                    "monthly_mortgage": house["monthly_mortgage"],
                    "lock_in": house["lock_in"],
                    "owned_equity": house["owned_equity"],
                },
                causes=[row["node"]],
            )
    return rows


def _reentry(
    actors, households, housing, originals, topology, rng, year, month, offers
):
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

        offer = v3._generate_offer(
            actor_id, actor, households[actor_id], rng, year, "reentry"
        )
        evaluation = _evaluate_offer_v4(
            actor_id, actor, households[actor_id], housing, offer
        )
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
            accepted_node = _accept_offer_v4(
                actor_id, actor, offer, evaluation, originals, housing, topology,
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
                "reentry_offer_rejected_after_finance_housing_check",
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


def _maybe_buy_home(
    actor_id, actor, household, housing, ledger, topology, rng, year, month
):
    if month != 3 or year not in HOME_BUY_YEARS:
        return None
    if actor["stage"] != "employed" or not actor.get("employment_terms"):
        return None
    house = housing[actor_id]
    if house["tenure"] != "rent":
        return None
    city = actor["city_state"]
    if city not in v3.CITY_BUNDLES:
        return None
    reference_rent = v3.CITY_BUNDLES[city]["housing_monthly"]
    downpayment = int(round(reference_rent * 28))
    cash = ledger.state["accounts"][actor_id]
    minimum_buffer = 26000 + int(12000 * actor["family_care_load"])
    if cash < downpayment + minimum_buffer or actor["stability"] < .60:
        return None

    buy_probability = v3._clip(
        .24
        + .30 * actor["stability"]
        + .10 * household["home_housing_security"]
        - .16 * actor["mobility"]
    )
    if rng.random() >= buy_probability:
        return None

    ledger.transfer(
        f"home-downpayment:{actor_id}:{year}",
        actor_id,
        "external:housing_sink",
        downpayment,
        "fictional home downpayment",
    )
    house.update({
        "tenure": "owned_mortgage",
        "property_city": city,
        "rent_city": None,
        "monthly_rent": 0,
        "monthly_mortgage": int(round(reference_rent * .76)),
        "owned_equity": downpayment,
        "lock_in": v3._clip(.55 + .18 * actor["stability"]),
        "secondary_rent": 0,
        "purchase_year": year,
    })
    actor["cash"] = float(ledger.state["accounts"][actor_id])
    actor["mobility"] = max(.05, actor["mobility"] - .14 * house["lock_in"])
    node = topology._node(
        "home_purchased_with_lock_in",
        base._when(year, month),
        actor=actor_id,
        target=city,
        payload={
            "downpayment": downpayment,
            "monthly_mortgage": house["monthly_mortgage"],
            "lock_in": round(house["lock_in"], 4),
            "cash_after": ledger.state["accounts"][actor_id],
        },
    )
    house["history"].append({
        "date": base._when(year, month),
        "event": "home_purchased",
        "city": city,
        "downpayment": downpayment,
        "node": node["id"],
    })
    return {
        "date": base._when(year, month),
        "actor": actor_id,
        "city": city,
        "downpayment": downpayment,
        "node": node["id"],
    }


def simulate_career_six_finance_housing(seed=1, design=None):
    """Run v4 with monthly double-entry cash and housing lock-in."""
    design = deepcopy(design or base.load_career_six_design())
    rng = random.Random(seed)
    topology = continuity._topology(design)
    actors, originals = continuity._initial_state(design, rng)
    households = v3._build_households(design, rng)
    housing = _initial_housing()
    ledger = _finance_ledger(design)
    for actor in actors.values():
        actor["bundle_rejections"] = 0
        actor["preferred_city_shift"] = None
        actor["employment_terms"] = None

    interactions, jobs, family, reassessments, reentries = [], [], [], [], []
    offers, finance_rows, home_purchases, snapshots = [], [], [], []

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
            event = v3._update_household(
                actor_id, actors[actor_id], households[actor_id], topology, rng, year, month
            )
            if event:
                family.append(event)

        finance_rows.extend(
            _advance_personal_finance(
                actors, households, housing, ledger, topology, year, month
            )
        )

        for actor_id in base.NEW_ACTORS:
            purchase = _maybe_buy_home(
                actor_id, actors[actor_id], households[actor_id], housing,
                ledger, topology, rng, year, month
            )
            if purchase:
                home_purchases.append(purchase)

        reassessments.extend(
            _reassess(actors, households, housing, topology, rng, year, month)
        )
        jobs.extend(
            _job_cycle(
                actors, households, housing, originals, topology,
                rng, year, month, offers
            )
        )
        reentries.extend(
            _reentry(
                actors, households, housing, originals, topology,
                rng, year, month, offers
            )
        )

        if month == 12:
            snapshots.append({
                "year": year,
                "actors": deepcopy(actors),
                "households": deepcopy(households),
                "housing": deepcopy(housing),
                "accounts": deepcopy(ledger.state["accounts"]),
                "original_core": deepcopy(originals),
            })

    return {
        "seed": seed,
        "status": "career_six_2026_2035_finance_housing_v4_noncanonical_scout",
        "start_date": design["start_date"],
        "end_date": design["end_date"],
        "actors": actors,
        "households": households,
        "housing": housing,
        "original_core": originals,
        "interactions": interactions,
        "job_cycles": jobs,
        "family_events": family,
        "reassessments": reassessments,
        "reentries": reentries,
        "offers": offers,
        "finance_rows": finance_rows,
        "home_purchases": home_purchases,
        "annual_snapshots": snapshots,
        "ledger": ledger.snapshot(),
        "topology": topology.snapshot(),
        "fixed_design_rules": deepcopy(design["fixed_design_rules"]),
        "engineering_prior_notice": "V4 salary, expense, housing and care values are fictional replay priors; the ledger enforces conservation within those priors.",
    }
