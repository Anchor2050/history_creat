"""Monte Carlo stress generator for the converged social world.

Coefficients are transparent engineering assumptions, not fitted estimates.
Purpose: falsify clean narrative arcs and expose combinations of constraints.
"""
import random, statistics

FUTURES=(
 ("slow_rebalance",.32,.05,.15,.05,-.10,-.10,-.10),
 ("long_adjustment",.23,-.40,-.10,-.25,-.25,-.10,-.20),
 ("social_dividend",.17,.30,.35,.25,.25,.20,-.05),
 ("unequal_productivity",.18,.10,-.20,.15,-.15,.05,-.15),
 ("fragmented_shock",.10,-.30,-.25,-.30,-.30,-.20,-.50),
)

def _pick(rng):
    u=rng.random(); c=0
    for f in FUTURES:
        c+=f[1]
        if u<=c: return f
    return FUTURES[-1]

def draw_world(rng):
    name,_,demand,security,mobility,care,climate,external=_pick(rng)
    parent_care=max(0,rng.gauss(.45-care*.35,.22))
    health=max(0,rng.gauss(.15-climate*.10,.10))
    housing_relief=rng.random()<max(.05,min(.8,.35+security*.4))
    trade_shock=rng.random()<max(.05,min(.7,.18-external*.5))
    chen_income=.65+.35*demand+.2*mobility-.25*trade_shock+rng.gauss(0,.12)
    chen_time=.55-.35*parent_care-.15*health+.15*security+rng.gauss(0,.10)
    chen_training_budget=.45+.35*demand+.3*security-.3*trade_shock+rng.gauss(0,.12)
    lin_option=.55+.3*security+.2*mobility+.15*housing_relief-.35*parent_care-.15*health+rng.gauss(0,.12)
    xu_reward=.45+.25*demand+.2*mobility-.2*trade_shock+rng.gauss(0,.14)
    dims=[chen_income,chen_time,lin_option,xu_reward,.6+.2*housing_relief-.2*parent_care]
    return {"future":name,"chen_income_exit":chen_income>.6,"chen_time_sovereignty":chen_time>.5,
      "chen_can_fund_humane_training":chen_training_budget>.6,"lin_option_value":lin_option>.55,
      "xu_market_reward":xu_reward>.55,"life_dimension_spread":statistics.pstdev(dims)}

def run(n=20000,seed=20261011):
    rng=random.Random(seed); rows=[draw_world(rng) for _ in range(n)]
    def rate(key,rs=rows): return sum(bool(r[key]) for r in rs)/len(rs)
    return {"n":n,"seed":seed,"overall":{
      "chen_income_exit":rate("chen_income_exit"),"chen_time_sovereignty":rate("chen_time_sovereignty"),
      "chen_can_fund_humane_training":rate("chen_can_fund_humane_training"),"lin_option_value":rate("lin_option_value"),
      "xu_market_reward":rate("xu_market_reward"),
      "chen_income_without_time":sum(r["chen_income_exit"] and not r["chen_time_sovereignty"] for r in rows)/n,
      "chen_income_without_training_budget":sum(r["chen_income_exit"] and not r["chen_can_fund_humane_training"] for r in rows)/n,
      "mean_life_dimension_spread":sum(r["life_dimension_spread"] for r in rows)/n},
      "epistemic_status":"engineering_stress_test_not_empirical_forecast"}
