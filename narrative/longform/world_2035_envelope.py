"""2031-2035 correlated social-world envelope.

Scenario labels are engineering envelopes, not claimed forecast probabilities.
The purpose is to alter feasible sets before characters choose.
"""

SCENARIOS_2031_2035 = {
    "managed_rebalancing": {
        "demand": .15, "safety_net": .35, "care_services": .25, "housing_liquidity": .05,
        "job_mobility": .20, "training_budget": .15, "external_stability": .10,
    },
    "long_adjustment": {
        "demand": -.35, "safety_net": .10, "care_services": .10, "housing_liquidity": -.30,
        "job_mobility": -.25, "training_budget": -.30, "external_stability": .00,
    },
    "productive_inclusive": {
        "demand": .25, "safety_net": .40, "care_services": .35, "housing_liquidity": .10,
        "job_mobility": .35, "training_budget": .35, "external_stability": .10,
    },
    "productive_unequal": {
        "demand": .10, "safety_net": .05, "care_services": .05, "housing_liquidity": -.05,
        "job_mobility": .05, "training_budget": -.10, "external_stability": .10,
    },
    "fragmented_external": {
        "demand": -.15, "safety_net": .15, "care_services": .15, "housing_liquidity": -.10,
        "job_mobility": -.10, "training_budget": -.20, "external_stability": -.45,
    },
    "care_heavy_transition": {
        "demand": -.05, "safety_net": .20, "care_services": -.25, "housing_liquidity": .00,
        "job_mobility": -.20, "training_budget": .00, "external_stability": .10,
    },
}

TRANSMISSION = {
    "safety_net": ("cash_floor", "exit_bad_job_option", "migration_risk_tolerance"),
    "care_services": ("family_care_hours", "care_cash_cost", "migration_feasibility"),
    "housing_liquidity": ("moving_cost", "wealth_buffer", "care_proximity_lockin"),
    "job_mobility": ("outside_options", "wage_bargaining", "city_switch_option"),
    "training_budget": ("junior_ladder", "paid_trial_feasibility", "midcareer_retraining"),
    "external_stability": ("employer_orders", "budget_variance", "layoff_risk"),
    "demand": ("hiring", "promotion_budget", "household_confidence"),
}

HARD_RULES = (
    "scenario values change opportunities, never dictate a character choice",
    "care requires a named person/institution to supply hours or money",
    "a welfare benefit only affects an actor after eligibility and information are established",
    "housing cannot simultaneously count as liquid wealth and zero-cost immobility",
    "organizational title and discretionary budget are separate resources",
    "social value and market price are separate state variables",
)


def scenario_packet(name):
    if name not in SCENARIOS_2031_2035:
        raise ValueError(name)
    return {
        "name": name,
        "years": (2031, 2035),
        "effects": dict(SCENARIOS_2031_2035[name]),
        "transmission": TRANSMISSION,
        "hard_rules": HARD_RULES,
        "epistemic_status": "engineering_scenario_envelope",
    }
