"""Historical extraction after social-world convergence.

A life is not a scalar stock of success. History records attempted conversions
between resources and who absorbs the conversion cost.
"""

RESOURCES=("money","time","care","health","housing","mobility","credential","expertise",
           "bargaining_power","institutional_authority","trust","social_protection","autonomy")
OUTCOMES=("success","blocked","hidden_cost","delayed","cost_transferred")


def conversion(actor, source, target, outcome, cost_bearers=(), delay_weeks=0, mechanism=None):
    if source not in RESOURCES or target not in RESOURCES: raise ValueError("unknown resource")
    if outcome not in OUTCOMES: raise ValueError("unknown conversion outcome")
    if outcome=="delayed" and delay_weeks<=0: raise ValueError("delayed conversion needs delay")
    if outcome=="cost_transferred" and not cost_bearers: raise ValueError("transferred cost needs bearer")
    return {"actor":actor,"source":source,"target":target,"outcome":outcome,
            "cost_bearers":list(cost_bearers),"delay_weeks":delay_weeks,"mechanism":mechanism}

PRIMARY_CONVERSIONS=(
    conversion("chen_lan","credential","money","delayed",delay_weeks=20,mechanism="post-PhD labor market"),
    conversion("chen_lan","money","time","blocked",mechanism="family care + client responsibility"),
    conversion("chen_lan","institutional_authority","autonomy","hidden_cost",cost_bearers=("chen_lan",),mechanism="management responsibility"),
    conversion("chen_lan","institutional_authority","trust","cost_transferred",cost_bearers=("firm_budget",),mechanism="paid junior training"),
    conversion("lin_jing","expertise","autonomy","hidden_cost",cost_bearers=("lin_jing",),mechanism="lower salary / narrower role choice"),
    conversion("lin_jing","housing","mobility","blocked",mechanism="ownership/commute/care can constrain relocation"),
    conversion("xu_hang","expertise","bargaining_power","delayed",delay_weeks=52,mechanism="verification reputation"),
    conversion("xu_hang","expertise","money","blocked",mechanism="social need for verification does not guarantee market premium"),
)


def historical_density(conversions=PRIMARY_CONVERSIONS):
    """Diversity is preferred to a pile of successful upward conversions."""
    kinds={c["outcome"] for c in conversions}
    resources={(c["source"],c["target"]) for c in conversions}
    bearers={b for c in conversions for b in c["cost_bearers"]}
    return {"outcome_variety":len(kinds),"resource_paths":len(resources),"cost_bearers":len(bearers),
            "has_blocked":any(c["outcome"]=="blocked" for c in conversions),
            "has_transferred_cost":any(c["outcome"]=="cost_transferred" for c in conversions)}
