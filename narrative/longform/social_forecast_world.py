"""Research-grounded 2026-2030 social forecast layer.

World state grows from observed 2026 anchors plus uncertain scenario pressures.
No forecast is a guaranteed future event. Actors only experience realized effects
through household, city, institution, labor, care, climate and cultural channels.
"""

SOCIAL_DOMAINS = (
    "macro_household", "demography_care", "housing_city", "education_status",
    "work_welfare", "family_intimacy", "climate_energy", "regional_mobility",
)

OBSERVED_2026 = {
    "macro_household": {
        "state": "growth remains resilient but domestic demand/property adjustment keep households cautious",
        "pressure": ["precautionary_saving", "uneven_income_confidence", "consumption_rebalancing_policy"],
    },
    "demography_care": {
        "state": "aging and very low fertility are structural; policy expands childcare, eldercare and family support",
        "pressure": ["parent_care_hours", "care_gender_bargaining", "eldercare_market", "fertility_policy_without_guaranteed_birth_response"],
    },
    "housing_city": {
        "state": "housing shifts from expansion toward stock renewal, rental/保障 and youth housing difficulty",
        "pressure": ["rent_buy_optionality", "old_neighborhood_renewal", "youth_stage_housing", "less_assured_property_wealth_effect"],
    },
    "education_status": {
        "state": "higher education links programs more tightly to labor demand and strategic fields; evaluation reform stresses contribution and integrity",
        "pressure": ["degree_signal_repricing", "program_reallocation", "professional_degree_growth", "research_evaluation_change"],
    },
    "work_welfare": {
        "state": "flexible/new-form employment expands while social protection is being extended; retirement is gradually delayed",
        "pressure": ["portfolio_careers", "social_insurance_portability", "longer_working_lives", "junior_senior_queueing"],
    },
    "family_intimacy": {
        "state": "low fertility desire, high childrearing cost and gendered family bargaining coexist with greater individual autonomy",
        "pressure": ["later_family_formation", "marriage_optionality", "care_work_negotiation", "digital_social_fragmentation"],
    },
    "climate_energy": {
        "state": "green transition accelerates while adaptation to extreme weather becomes a routine governance problem",
        "pressure": ["heat_flood_disruption", "green_skill_demand", "energy_cost_transition", "urban_resilience_investment"],
    },
    "regional_mobility": {
        "state": "urbanization continues but becomes more differentiated: young people cluster in major/provincial cities while city-to-city and near-region mobility rise",
        "pressure": ["city_tier_tradeoffs", "return_or_stay", "metropolitan_commuting", "regional_opportunity_divergence"],
    },
}

# Scenario weights are priors for world generation, not probabilities claimed by sources.
SCENARIOS_2027_2030 = {
    "baseline_rebalancing": {"weight": .45, "effects": {
        "macro_household": .10, "demography_care": .20, "housing_city": .10,
        "education_status": .15, "work_welfare": .15, "family_intimacy": .10,
        "climate_energy": .15, "regional_mobility": .10}},
    "weak_demand_long_adjustment": {"weight": .25, "effects": {
        "macro_household": -.35, "demography_care": -.05, "housing_city": -.30,
        "education_status": -.10, "work_welfare": -.25, "family_intimacy": -.15,
        "climate_energy": .05, "regional_mobility": -.05}},
    "productivity_social_dividend": {"weight": .15, "effects": {
        "macro_household": .30, "demography_care": .20, "housing_city": .15,
        "education_status": .25, "work_welfare": .25, "family_intimacy": .10,
        "climate_energy": .25, "regional_mobility": .20}},
    "fragmented_transition": {"weight": .15, "effects": {
        "macro_household": -.15, "demography_care": -.15, "housing_city": -.05,
        "education_status": .05, "work_welfare": -.20, "family_intimacy": -.20,
        "climate_energy": -.10, "regional_mobility": -.20}},
}

WORLD_CHANNELS = {
    "household": ["cash_buffer", "care_hours", "housing_tenure", "parent_transfer", "childbearing_option"],
    "city": ["rent", "commute", "heat_days", "public_services", "job_density"],
    "institution": ["headcount", "evaluation", "training_slots", "retirement_turnover", "research_funding"],
    "organization": ["wages", "hours", "benefits", "promotion", "training_budget", "layoff_risk"],
    "relationship": ["time_together", "care_bargain", "income_gap", "migration_distance", "status_comparison"],
}


def forecast_packet(year, scenario="baseline_rebalancing"):
    if year < 2026 or year > 2030:
        raise ValueError("forecast layer currently covers 2026-2030")
    if scenario not in SCENARIOS_2027_2030:
        raise ValueError("unknown scenario")
    return {
        "year": year,
        "scenario": scenario,
        "observed_2026": OBSERVED_2026,
        "scenario_effects": {} if year == 2026 else SCENARIOS_2027_2030[scenario]["effects"],
        "channels": WORLD_CHANNELS,
        "epistemic_status": "observed_anchor_plus_uncertain_forecast" if year > 2026 else "observed_anchor",
    }
