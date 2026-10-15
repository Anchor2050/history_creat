"""Session target: run 32x160, audit causal validity, mine diverse candidates."""
from copy import deepcopy
from .endogenous_world import simulate_endogenous_world
from .macro_world import beijing_2026_macro
from .multiverse import _inject_seeded_shocks, world_specs
from .story_miner import pareto_mine

def _macro_for(spec): return _inject_seeded_shocks(beijing_2026_macro(),spec)
def run_session_pipeline(count=32,weeks=160,master_seed=20261011):
 specs=world_specs(count,master_seed); runs=[]
 for spec in specs:
  run=simulate_endogenous_world(spec["seed"],weeks,_macro_for(spec)); run["spec"]=deepcopy(spec); runs.append(run)
 audit=audit_runs(runs); candidates=pareto_mine(runs,min(8,count))
 return {"version":2,"count":count,"weeks":weeks,"world_weeks":count*weeks,"master_seed":master_seed,"audit":audit,"candidates":candidates,"runs":runs,"status":"complete_requires_deep_replay" if audit["passes"] else "complete_audit_failed"}
def audit_runs(runs):
 total=sum(len(r["cross_actor_chains"]) for r in runs); with_chain=sum(bool(r["cross_actor_chains"]) for r in runs); with_life=sum(bool(r["lifecycle"]) for r in runs); neg=sum(not r["no_negative_cash"] for r in runs); hardship=sum(bool(r.get("hardship_events")) for r in runs); logged=all(all(e.get("provenance",{}).get("kind")=="seeded_exogenous_event" for e in r["external_events"]) for r in runs)
 passes=bool(runs) and with_life==len(runs) and logged and with_chain>=max(1,len(runs)//2) and total>=len(runs) and neg==0
 return {"worlds":len(runs),"total_cross_actor_chains":total,"worlds_with_cross_actor_chain":with_chain,"worlds_with_lifecycle_change":with_life,"negative_cash_worlds":neg,"worlds_with_explicit_hardship":hardship,"seeded_external_events_all_logged":logged,"passes":passes,"gate":"all worlds lifecycle; >=half worlds cross-actor; >=1 chain/world on average; zero impossible negative cash; all seeded events logged"}
