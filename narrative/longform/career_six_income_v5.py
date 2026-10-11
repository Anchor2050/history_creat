"""Income-prior pass v5 for the six-character 2026-2035 branch.

V5 keeps the finance/housing mechanics from v4 but replaces its implicit
zero-income pre-employment stress prior with explicit, seed-varying doctoral,
family-support, search-support and temporary-work streams.
"""
from copy import deepcopy
import json
from pathlib import Path
import random

from . import career_six_2035 as base
from . import career_six_continuity_v2 as continuity
from . import career_six_household_city_v3 as v3
from . import career_six_finance_housing_v4 as v4
from .ledger import Ledger


def load_income_priors(path=None):
    if path is None:
        path = (
            Path(__file__).resolve().parents[2]
            / "docs" / "scenarios" / "career-six-income-priors-v1.json"
        )
    with open(path, encoding="utf-8") as handle:
        priors = json.load(handle)
    if priors.get("spec_version") != 1:
        raise ValueError("income priors require spec_version 1")
    return priors


def _draw_income_profiles(design, priors, rng):
    profiles = {}
    stipend = priors["doctoral_stipend_monthly"]
    family = priors["family_support_monthly"]
    search = priors["search_period_support_monthly"]
    net = priors["employment_net_pay_share"]
    for actor_id, actor in design["actors"].items():
        temporary = priors["temporary_work"][actor["field"]]
        profiles[actor_id] = {
            "doctoral_stipend_monthly": rng.randint(stipend["min"], stipend["max"]),
            "family_support_monthly": rng.randint(family["min"], family["max"]),
            "search_support_monthly": rng.randint(search["min"], search["max"]),
            "employment_net_pay_share": rng.uniform(net["min"], net["max"]),
            "temporary_work": deepcopy(temporary),
        }
    return profiles


def _finance_ledger_v5(design):
    accounts = {actor_id: int(row["cash"]) for actor_id, row in design["actors"].items()}
    accounts.update({
        "external:salary_pool": 100_000_000,
        "external:stipend_pool": 30_000_000,
        "external:family_support_pool": 30_000_000,
        "external:temporary_work_pool": 30_000_000,
        "external:search_support_pool": 30_000_000,
        "external:living_sink": 0,
        "external:housing_sink": 0,
        "external:care_sink": 0,
        "external:relocation_sink": 0,
    })
    weekly = {
        actor_id: int(row["weekly_discretionary_work_hours"])
        for actor_id, row in design["actors"].items()
    }
    return Ledger("2026-03-02", accounts, weekly)


def _income_transfer(ledger, actor_id, year, month, source, amount, label):
    amount = max(0, int(round(amount)))
    if not amount:
        return 0
    ledger.transfer(
        f"{label}:{actor_id}:{year:04d}-{month:02d}",
        source,
        actor_id,
        amount,
        label.replace("_", " "),
    )
    return amount


def _advance_personal_finance_v5(
    actors, households, housing, ledger, income_profiles, topology, rng, year, month
):
    when = v4._ledger_when(year, month)
    ledger.advance(when)
    rows = []
    for actor_id in base.NEW_ACTORS:
        actor = actors[actor_id]
        profile = income_profiles[actor_id]
        house = housing[actor_id]
        employment_income = 0
        stipend_income = 0
        family_income = 0
        search_income = 0
        temporary_income = 0

        if actor["stage"] == "employed" and actor.get("employment_terms"):
            employment_income = _income_transfer(
                ledger,
                actor_id,
                year,
                month,
                "external:salary_pool",
                actor["employment_terms"]["monthly_gross"] * profile["employment_net_pay_share"],
                "employment_income",
            )
        elif actor["stage"] == "doctoral":
            stipend_income = _income_transfer(
                ledger,
                actor_id,
                year,
                month,
                "external:stipend_pool",
                profile["doctoral_stipend_monthly"],
                "doctoral_stipend",
            )
            family_income = _income_transfer(
                ledger,
                actor_id,
                year,
                month,
                "external:family_support_pool",
                profile["family_support_monthly"],
                "family_support",
            )
            temporary = profile["temporary_work"]
            if rng.random() < temporary["monthly_probability_doctoral"]:
                temporary_income = _income_transfer(
                    ledger,
                    actor_id,
                    year,
                    month,
                    "external:temporary_work_pool",
                    rng.randint(temporary["income_if_active_min"], temporary["income_if_active_max"]),
                    "temporary_work_income",
                )
        else:
            search_income = _income_transfer(
                ledger,
                actor_id,
                year,
                month,
                "external:search_support_pool",
                profile["search_support_monthly"],
                "search_period_support",
            )
            family_income = _income_transfer(
                ledger,
                actor_id,
                year,
                month,
                "external:family_support_pool",
                profile["family_support_monthly"],
                "family_support",
            )
            temporary = profile["temporary_work"]
            if rng.random() < temporary["monthly_probability_search"]:
                temporary_income = _income_transfer(
                    ledger,
                    actor_id,
                    year,
                    month,
                    "external:temporary_work_pool",
                    rng.randint(temporary["income_if_active_min"], temporary["income_if_active_max"]),
                    "temporary_work_income",
                )

        living_requested = v4.CITY_LIVING_MONTHLY.get(house["work_city"], 2400)
        housing_requested = v4._housing_monthly_cost(house)
        care_requested = int(round(
            2300
            * actor["family_care_load"]
            * (1.0 + .35 * households[actor_id]["unmet_care"])
        ))
        living = v4._transfer_up_to(
            ledger,
            f"living:{actor_id}:{year:04d}-{month:02d}",
            actor_id,
            "external:living_sink",
            living_requested,
            "monthly living costs",
        )
        housing_paid = v4._transfer_up_to(
            ledger,
            f"housing:{actor_id}:{year:04d}-{month:02d}",
            actor_id,
            "external:housing_sink",
            housing_requested,
            "rent/mortgage/secondary housing costs",
        )
        care = v4._transfer_up_to(
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
            "employment_income": employment_income,
            "doctoral_stipend": stipend_income,
            "family_support": family_income,
            "search_support": search_income,
            "temporary_income": temporary_income,
            "living_paid": living["paid"],
            "housing_paid": housing_paid["paid"],
            "care_paid": care["paid"],
            "unmet": unmet,
            "cash_after": ledger.state["accounts"][actor_id],
            "node": unmet_node,
        })
    return rows


def simulate_career_six_income(seed=1, design=None, priors=None):
    """Run v5 with explicit pre-employment income priors."""
    design = deepcopy(design or base.load_career_six_design())
    priors = deepcopy(priors or load_income_priors())
    rng = random.Random(seed)
    topology = continuity._topology(design)
    actors, originals = continuity._initial_state(design, rng)
    households = v3._build_households(design, rng)
    housing = v4._initial_housing()
    income_profiles = _draw_income_profiles(design, priors, rng)
    ledger = _finance_ledger_v5(design)
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
            _advance_personal_finance_v5(
                actors, households, housing, ledger, income_profiles,
                topology, rng, year, month
            )
        )
        for actor_id in base.NEW_ACTORS:
            purchase = v4._maybe_buy_home(
                actor_id, actors[actor_id], households[actor_id], housing,
                ledger, topology, rng, year, month
            )
            if purchase:
                home_purchases.append(purchase)

        reassessments.extend(
            v4._reassess(actors, households, housing, topology, rng, year, month)
        )
        jobs.extend(
            v4._job_cycle(
                actors, households, housing, originals, topology,
                rng, year, month, offers
            )
        )
        reentries.extend(
            v4._reentry(
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
                "income_profiles": deepcopy(income_profiles),
                "accounts": deepcopy(ledger.state["accounts"]),
                "original_core": deepcopy(originals),
            })

    return {
        "seed": seed,
        "status": "career_six_2026_2035_income_v5_noncanonical_scout",
        "start_date": design["start_date"],
        "end_date": design["end_date"],
        "actors": actors,
        "households": households,
        "housing": housing,
        "income_profiles": income_profiles,
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
        "income_prior_rules": deepcopy(priors["audit_rules"]),
        "fixed_design_rules": deepcopy(design["fixed_design_rules"]),
        "engineering_prior_notice": priors["notice"],
    }


def summarize_income_sensitivity(seeds=range(1, 9)):
    """Return compact diagnostics; this does not select a canonical world."""
    summaries = []
    purchase_counts = {actor_id: 0 for actor_id in base.NEW_ACTORS}
    hardship_counts = {actor_id: 0 for actor_id in base.NEW_ACTORS}
    destinations = {actor_id: set() for actor_id in base.NEW_ACTORS}
    for seed in seeds:
        run = simulate_career_six_income(seed=seed)
        for row in run["home_purchases"]:
            purchase_counts[row["actor"]] += 1
        for row in run["finance_rows"]:
            if row["unmet"]:
                hardship_counts[row["actor"]] += 1
        for actor_id in base.NEW_ACTORS:
            actor = run["actors"][actor_id]
            destinations[actor_id].add((actor["sector"], actor["city_state"]))
        summaries.append({
            "seed": seed,
            "home_purchases": len(run["home_purchases"]),
            "hardship_months": sum(1 for row in run["finance_rows"] if row["unmet"]),
            "offer_rejections": sum(1 for row in run["job_cycles"] + run["reentries"] if row["outcome"] == "offer_rejected"),
        })
    return {
        "runs": summaries,
        "purchase_counts": purchase_counts,
        "hardship_counts": hardship_counts,
        "destination_variety": {actor_id: len(values) for actor_id, values in destinations.items()},
        "status": "sensitivity_diagnostic_noncanonical",
    }
