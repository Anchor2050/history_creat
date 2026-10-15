"""Second-generation social forecast world: society first, characters second.

The layer separates observed 2026 anchors from uncertain 2027-2030 trajectories.
Scenario priors are modeling assumptions, never source-claimed probabilities.
"""

DOMAINS = (
    "domestic_demand", "property_housing", "labor_market", "social_protection",
    "aging_care", "fertility_family", "health_mental", "education_credentials",
    "urban_form", "regional_mobility", "climate_resilience", "trade_fragmentation",
    "organizational_power", "culture_status",
)

ANCHORS_2026 = {
    "domestic_demand": "growth remains positive while cautious households and property adjustment restrain demand",
    "property_housing": "housing policy shifts toward stock renewal, rental,保障 and youth/new-resident access",
    "labor_market": "employment policy explicitly targets structural mismatch, youth employment and technology-related displacement risk",
    "social_protection": "policy direction broadens unemployment, injury and new-form worker protection and portability",
    "aging_care": "aging, long-term care, community eldercare and family care burden become structural institutions",
    "fertility_family": "birth support expands through childcare, insurance and family policy without assuming fertility rebounds",
    "health_mental": "health policy expands life-cycle, occupational and mental-health services and climate-health adaptation",
    "education_credentials": "education is pushed toward labor-demand alignment while degree signals face repricing",
    "urban_form": "urban development shifts from expansion toward renewal, complete communities and resilient infrastructure",
    "regional_mobility": "metropolitan integration and city differentiation change the stay/return decision",
    "climate_resilience": "heat, flood and climate-health adaptation increasingly enter ordinary city governance",
    "trade_fragmentation": "external trade remains important while US-China fragmentation and supply-chain rerouting raise uncertainty",
    "organizational_power": "firms face pressure to raise productivity while deciding who captures gains and who bears transition costs",
    "culture_status": "old success markers--degree, home ownership, stable title--remain powerful but become less sufficient as universal rankings",
}

# Latent forces are deliberately fewer than domains: correlated futures matter more
# than independently randomizing every social variable.
FUTURES = {
    "slow_rebalance": {
        "prior": .32,
        "forces": {"demand": .05, "security": .15, "mobility": .05, "care": -.10, "climate": -.10, "external": -.10}},
    "long_adjustment": {
        "prior": .23,
        "forces": {"demand": -.40, "security": -.10, "mobility": -.25, "care": -.25, "climate": -.10, "external": -.20}},
    "social_dividend": {
        "prior": .17,
        "forces": {"demand": .30, "security": .35, "mobility": .25, "care": .25, "climate": .20, "external": -.05}},
    "unequal_productivity": {
        "prior": .18,
        "forces": {"demand": .10, "security": -.20, "mobility": .15, "care": -.15, "climate": .05, "external": -.15}},
    "fragmented_shock": {
        "prior": .10,
        "forces": {"demand": -.30, "security": -.25, "mobility": -.30, "care": -.30, "climate": -.20, "external": -.50}},
}

TRANSMISSION = {
    "household": ("income_confidence", "precautionary_saving", "care_hours", "health_shock_buffer", "housing_optionality"),
    "city": ("rent_burden", "commute", "public_service_access", "heat_flood_disruption", "job_density"),
    "university": ("headcount", "training_rungs", "evaluation_rules", "funding", "retirement_turnover"),
    "firm": ("wage_budget", "training_budget", "layoff_risk", "promotion_rules", "benefit_quality", "client_demand"),
    "family": ("parent_care", "intergenerational_transfer", "marriage_pressure", "childbearing_cost", "migration_bargain"),
    "relationship": ("time_scarcity", "income_comparison", "distance", "care_fairness", "status_language"),
}

# Directional interactions: these are hypotheses to stress-test, not empirical coefficients.
INTERACTIONS = (
    ("weak_property", "precautionary_saving", "domestic_demand"),
    ("better_social_protection", "lower_precautionary_saving", "domestic_demand"),
    ("aging", "family_care_hours", "career_optionality"),
    ("childcare_access", "care_bargaining", "family_formation"),
    ("urban_renewal", "housing_optionality", "migration_choice"),
    ("trade_fragmentation", "firm_volatility", "knowledge_worker_security"),
    ("climate_extremes", "care_and_commute_disruption", "time_budget"),
    ("credential_repricing", "training_rungs", "young_worker_transition"),
)


def future_packet(name):
    if name not in FUTURES:
        raise ValueError("unknown future")
    return {
        "name": name,
        "prior": FUTURES[name]["prior"],
        "forces": dict(FUTURES[name]["forces"]),
        "anchors": dict(ANCHORS_2026),
        "transmission": TRANSMISSION,
        "interactions": INTERACTIONS,
        "epistemic_status": "research_anchored_scenario_not_prediction_fact",
    }
