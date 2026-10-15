"""Convergence protocol: research -> world -> lives -> history.

Do not converge because a theme feels satisfying. Converge when the causal trunk
is robust to plausible social futures and remaining uncertainty is localized.
"""

from .social_forecast_world import SCENARIOS_2027_2030

CONVERGENCE_GATES = (
    "scenario_robust_trunk",
    "contingencies_marked",
    "persistent_material_state",
    "persistent_relationship_state",
    "persistent_institution_state",
    "no_future_knowledge_leak",
    "no_theme_deus_ex_machina",
)

# Claims from the current trunk that should be stress-tested rather than assumed.
TRUNK_HYPOTHESES = {
    "chen_material_rise_after_graduation": {"robust_expected": True},
    "chen_second_graduation_into_responsibility": {"robust_expected": False},
    "lin_autonomy_has_real_material_cost": {"robust_expected": True},
    "xu_failure_archive_becomes_market_capital": {"robust_expected": False},
    "friendship_survives_income_status_divergence": {"robust_expected": False},
    "care_burden_reenters_career_after_income_rise": {"robust_expected": True},
    "housing_choice_changes_geographic_optionality": {"robust_expected": True},
    "young_worker_training_cost_shifts_to_organizations": {"robust_expected": False},
}


def convergence_report(outcomes_by_scenario):
    scenarios=set(SCENARIOS_2027_2030)
    if set(outcomes_by_scenario) != scenarios:
        raise ValueError("need one outcome map for every social scenario")
    keys=set.intersection(*(set(v) for v in outcomes_by_scenario.values()))
    robust={}
    contingent={}
    for key in sorted(keys):
        values={name: bool(outcomes_by_scenario[name][key]) for name in scenarios}
        if len(set(values.values())) == 1:
            robust[key]=next(iter(values.values()))
        else:
            contingent[key]=values
    return {
        "robust": robust,
        "contingent": contingent,
        "converged": bool(robust) and len(contingent) <= max(2, len(keys)//2),
        "rule": "robust trunk may become history; contingent branches remain visibly conditional",
    }
