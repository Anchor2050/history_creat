"""Bridge slow public-world changes into actor-visible context.

This module translates MacroWorld signals into bounded, actor-specific notices.
It never mutates money, permissions, consent, artifacts, relationships or plans.
"""
from copy import deepcopy

from .macro_world import MacroWorldError


DEFAULT_EXPOSURES = {
    "lin_jing": {
        "academic_job_availability": 1.0,
        "ai_research_capability": 0.5,
        "urban_housing_cost": 0.6,
        "university_discretionary_budget": 0.3,
    },
    "chen_lan": {
        "academic_job_availability": 1.2,
        "ai_research_capability": 0.4,
        "urban_housing_cost": 0.9,
        "research_outsourcing_demand": 0.7,
    },
    "xu_hang": {
        "academic_job_availability": 0.9,
        "ai_research_capability": 1.0,
        "urban_housing_cost": 0.5,
        "university_discretionary_budget": 0.4,
    },
    "wu_cheng": {
        "academic_job_availability": 0.4,
        "ai_research_capability": 0.5,
        "university_discretionary_budget": 1.0,
    },
    "shen_yan": {
        "academic_job_availability": 0.4,
        "ai_research_capability": 0.6,
        "university_discretionary_budget": 1.0,
    },
    "gu_wei": {
        "academic_job_availability": 0.4,
        "ai_research_capability": 0.8,
        "university_discretionary_budget": 0.8,
    },
    "zhao_ke": {
        "ai_research_capability": 0.8,
        "research_outsourcing_demand": 1.2,
    },
    "sun_jie": {
        "academic_job_availability": 0.2,
        "ai_research_capability": 0.2,
        "urban_housing_cost": 0.3,
        "university_discretionary_budget": 0.5,
    },
}


NOTICE_RULES = {
    "academic_job_availability": [
        (lambda v: v <= 0.90, "early_career_market_tight",
         "Early-career academic hiring has become visibly tighter than the 2026 reference period."),
    ],
    "ai_research_capability": [
        (lambda v: v >= 1.30, "research_automation_broadens",
         "Research automation tools can now complete a wider range of routine research tasks."),
        (lambda v: v >= 1.75, "research_automation_changes_work",
         "Research automation is beginning to change how some research jobs are scoped and evaluated."),
    ],
    "urban_housing_cost": [
        (lambda v: v >= 1.08, "housing_burden_rises",
         "Housing costs have risen enough to affect ordinary early-career planning."),
    ],
    "university_discretionary_budget": [
        (lambda v: v <= 0.90, "research_budget_tight",
         "Discretionary university research spending has become tighter."),
    ],
    "research_outsourcing_demand": [
        (lambda v: v >= 1.08, "outsourcing_demand_rises",
         "Demand for external research-service work has increased."),
    ],
}


class MacroBridgeError(ValueError):
    pass


def actor_macro_view(macro_world, actor_id, exposures=None):
    """Return only the macro facts this actor is materially exposed to."""
    exposures = exposures or DEFAULT_EXPOSURES
    if actor_id not in exposures:
        raise MacroBridgeError(f"No macro exposure profile for {actor_id}")
    profile = deepcopy(exposures[actor_id])
    try:
        pressure = macro_world.pressures_for(profile)
    except MacroWorldError as exc:
        raise MacroBridgeError(str(exc)) from None

    snapshot = macro_world.snapshot()
    notices = []
    for signal, weight in profile.items():
        if weight <= 0:
            continue
        value = snapshot["signals"][signal]["value"]
        for predicate, code, text in NOTICE_RULES.get(signal, []):
            if predicate(value):
                notices.append({
                    "code": code,
                    "signal": signal,
                    "public_fact": text,
                })

    # Include dated public shocks that touch an exposed signal. No private facts.
    recent_public_changes = []
    for event in snapshot["events"][-12:]:
        for shock in event.get("shocks", []):
            if shock["signal"] in profile and profile[shock["signal"]] > 0:
                recent_public_changes.append({
                    "month": event["month"],
                    "change_id": shock["change_id"],
                    "public_fact": shock["public_fact"],
                    "provenance": shock["provenance"],
                })

    return {
        "month": snapshot["now"],
        "actor": actor_id,
        "pressure": pressure,
        "notices": notices,
        "recent_public_changes": recent_public_changes,
    }


def freeze_macro_views(macro_world, actor_ids, exposures=None):
    """Freeze one monthly view per actor so sequential decisions do not leak."""
    return {
        actor_id: actor_macro_view(macro_world, actor_id, exposures)
        for actor_id in actor_ids
    }
