"""2030-2035 social-world extension, pass 01.

This file contains scenario mechanisms, not predictions presented as facts.
It extends conversion-history with institutional asynchrony and conversion lag.
"""

WORLD_2035_REGIMES = {
    "managed_rebalancing": {
        "household_security": +0.20, "job_entry": +0.05, "training": +0.15,
        "care_services": +0.20, "housing_optionality": +0.15, "external_demand": 0.00,
    },
    "long_adjustment": {
        "household_security": -0.15, "job_entry": -0.25, "training": -0.20,
        "care_services": +0.05, "housing_optionality": +0.05, "external_demand": -0.10,
    },
    "inclusive_productivity": {
        "household_security": +0.30, "job_entry": +0.10, "training": +0.30,
        "care_services": +0.25, "housing_optionality": +0.20, "external_demand": +0.05,
    },
    "unequal_productivity": {
        "household_security": -0.05, "job_entry": -0.20, "training": -0.15,
        "care_services": +0.10, "housing_optionality": 0.00, "external_demand": +0.05,
    },
    "fragmented_external": {
        "household_security": -0.10, "job_entry": -0.15, "training": -0.10,
        "care_services": +0.05, "housing_optionality": 0.00, "external_demand": -0.35,
    },
}

# Overlays may coexist with any macro regime.
OVERLAYS_2030_2035 = {
    "care_squeeze": {"care_hours": +0.40, "care_cash": +0.25, "mobility": -0.30},
    "care_service_catchup": {"care_hours": -0.20, "care_cash": +0.05, "mobility": +0.10},
    "extreme_weather_year": {"health_time": +0.15, "commute_reliability": -0.20, "city_service_value": +0.15},
    "regional_job_boom": {"mobility": +0.20, "outside_beijing_job_access": +0.30},
    "beijing_hiring_freeze": {"beijing_job_access": -0.35, "status_competition": +0.15},
}

CONVERSION_EDGES = {
    "skill_to_income": {"institutions": ("job_entry", "external_demand")},
    "skill_to_bargaining_power": {"institutions": ("job_entry", "training")},
    "income_to_time": {"institutions": ("care_services", "household_security")},
    "welfare_to_refusal_power": {"institutions": ("household_security",)},
    "housing_to_security": {"institutions": ("housing_optionality", "household_security")},
    "housing_to_mobility": {"institutions": ("housing_optionality",)},
    "organizational_power_to_good_institution": {"institutions": ("training", "external_demand")},
    "social_value_to_market_value": {"institutions": ("job_entry", "external_demand")},
    "family_intimacy_to_care_obligation": {"institutions": ("care_services",)},
}

# Project hypotheses. Lags are qualitative bins, not calibrated forecasts.
LAG_HYPOTHESES = {
    "verification_value": "social need may rise years before pay/status classifications catch up",
    "care_infrastructure": "service capacity may improve after household care burden has already risen",
    "degree_repricing": "program/enrollment adjustment follows labor-market evidence with institutional delay",
    "welfare_portability": "formal coverage can improve before people trust it enough to change saving or job-refusal behavior",
    "urban_renewal": "physical renewal can precede changes in commute, care access, rent and neighborhood attachment",
}


def regime_packet(regime, overlays=()):
    if regime not in WORLD_2035_REGIMES:
        raise ValueError("unknown 2035 regime")
    bad = [x for x in overlays if x not in OVERLAYS_2030_2035]
    if bad:
        raise ValueError(f"unknown overlays: {bad}")
    return {
        "regime": regime,
        "base": dict(WORLD_2035_REGIMES[regime]),
        "overlays": {x: dict(OVERLAYS_2030_2035[x]) for x in overlays},
        "epistemic_status": "project_scenario_not_forecast_fact",
    }
