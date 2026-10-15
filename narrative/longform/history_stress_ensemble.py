"""Stress the converged history against correlated social futures.

Scores are modeling judgments used to decide what may enter the historical
spine. They are not forecasts or empirical probabilities.
"""
from .social_forecast_world_v2 import FUTURES

CLAIMS = {
 "chen_material_exit": {"slow_rebalance":.90,"long_adjustment":.65,"social_dividend":.95,"unequal_productivity":.85,"fragmented_shock":.45},
 "chen_second_graduation": {"slow_rebalance":.80,"long_adjustment":.70,"social_dividend":.70,"unequal_productivity":.95,"fragmented_shock":.65},
 "lin_autonomy_tradeoff": {"slow_rebalance":.85,"long_adjustment":.90,"social_dividend":.70,"unequal_productivity":.90,"fragmented_shock":.80},
 "xu_verification_value": {"slow_rebalance":.75,"long_adjustment":.55,"social_dividend":.80,"unequal_productivity":.90,"fragmented_shock":.60},
 "family_care_pressure": {"slow_rebalance":.80,"long_adjustment":.90,"social_dividend":.55,"unequal_productivity":.85,"fragmented_shock":.95},
 "housing_not_single_score": {"slow_rebalance":.90,"long_adjustment":.95,"social_dividend":.80,"unequal_productivity":.90,"fragmented_shock":.90},
 "paid_training_ethic_survives": {"slow_rebalance":.70,"long_adjustment":.40,"social_dividend":.85,"unequal_productivity":.55,"fragmented_shock":.25},
 "winner_question_dissolves": {"slow_rebalance":.85,"long_adjustment":.80,"social_dividend":.75,"unequal_productivity":.90,"fragmented_shock":.80},
}


def evaluate_claim(name):
    scores=CLAIMS[name]
    weighted=sum(FUTURES[k]["prior"]*scores[k] for k in FUTURES)
    worst=min(scores.values())
    spread=max(scores.values())-worst
    # Spine requires robustness; conditional history may remain valuable without it.
    if weighted >= .78 and worst >= .60:
        status="spine"
    elif weighted >= .62:
        status="conditional_branch"
    else:
        status="texture_or_open_question"
    return {"claim":name,"weighted_robustness":round(weighted,3),"worst_case":round(worst,3),"spread":round(spread,3),"status":status}


def convergence_report():
    rows=[evaluate_claim(k) for k in CLAIMS]
    return {
      "rows":rows,
      "spine":[r["claim"] for r in rows if r["status"]=="spine"],
      "conditional":[r["claim"] for r in rows if r["status"]=="conditional_branch"],
      "open":[r["claim"] for r in rows if r["status"]=="texture_or_open_question"],
    }
