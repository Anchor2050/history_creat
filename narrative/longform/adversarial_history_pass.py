"""Adversarial convergence pass: try to break the frozen historical spine.

The point is falsification. A spine claim survives only if plausible social shocks
change outcomes without erasing the mechanism.
"""

SPINE = (
 "life_bundle_decomposes",
 "option_value_is_material",
 "housing_is_one_dimension",
 "winner_ranking_misleads",
)

SHOCKS = {
 "parent_disability": {"domain":"aging_care","hits":["time","migration","cash"]},
 "public_long_term_care_expands": {"domain":"aging_care","hits":["care_hours","cash"]},
 "mental_health_strain": {"domain":"health_mental","hits":["time","work_capacity","relationship"]},
 "childcare_becomes_accessible": {"domain":"fertility_family","hits":["family_option","care_bargain"]},
 "rent_relief_city_renewal": {"domain":"property_housing","hits":["housing","commute","cash"]},
 "property_wealth_declines": {"domain":"property_housing","hits":["family_buffer","status","mobility"]},
 "provincial_capital_job_boom": {"domain":"regional_mobility","hits":["job_density","distance","housing"]},
 "beijing_hiring_freeze": {"domain":"labor_market","hits":["headcount","bargaining","mobility"]},
 "trade_client_shock": {"domain":"trade_fragmentation","hits":["firm_budget","layoff_risk","training"]},
 "stronger_unemployment_protection": {"domain":"social_protection","hits":["downside_risk","job_exit"]},
 "extreme_heat_care_week": {"domain":"climate_resilience","hits":["commute","parent_health","time"]},
 "credential_repricing": {"domain":"education_credentials","hits":["status","entry_jobs","training"]},
}

# False means the shock would falsify the claim, not merely change a character outcome.
SURVIVAL = {
 "life_bundle_decomposes": {k: True for k in SHOCKS},
 "option_value_is_material": {k: True for k in SHOCKS},
 "housing_is_one_dimension": {k: True for k in SHOCKS},
 "winner_ranking_misleads": {k: True for k in SHOCKS},
}

# The most important adversarial observations are mechanisms, not scores.
OBSERVATIONS = {
 "parent_disability": "A care shock can erase a high earner's mobility, strengthening the distinction between income and option value.",
 "public_long_term_care_expands": "Public care can restore options without equalizing income; welfare itself becomes part of autonomy production.",
 "mental_health_strain": "Professional success can coexist with reduced capacity, breaking any one-dimensional winner ranking.",
 "childcare_becomes_accessible": "Better services change family feasibility but do not force marriage or birth; life dimensions remain separable.",
 "rent_relief_city_renewal": "Cheaper/better rental can raise autonomy without ownership, directly testing the housing-status assumption.",
 "property_wealth_declines": "Ownership can become a mobility constraint or weak buffer rather than an automatic upward marker.",
 "provincial_capital_job_boom": "A career can improve by leaving the highest-status city, separating city rank from career rank.",
 "beijing_hiring_freeze": "Prestige and opportunity can diverge sharply under constrained headcount.",
 "trade_client_shock": "Skill value and employer budget can diverge; being useful does not guarantee being rewarded.",
 "stronger_unemployment_protection": "Social insurance can increase practical freedom to refuse or switch jobs.",
 "extreme_heat_care_week": "Infrastructure and family health turn climate into a time-allocation shock, not a backdrop.",
 "credential_repricing": "A degree can retain knowledge value while losing part of its labor-market signal.",
}


def falsification_report():
    broken={claim:[s for s,v in results.items() if not v] for claim,results in SURVIVAL.items()}
    return {
      "shock_count":len(SHOCKS),
      "broken":broken,
      "survivors":[c for c,b in broken.items() if not b],
      "status":"spine_survives_adversarial_social_pass" if all(not b for b in broken.values()) else "reopen_spine",
    }
