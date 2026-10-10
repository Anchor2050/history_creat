"""Endogenous long-horizon social simulator for multiverse scouting.

External events are seeded and logged. Actor requests are deterministic responses
to a frozen weekly state. Scarcity is resolved only after every request is
formed, so two people can genuinely compete for one resource. Cash cannot cross
below zero: an uncovered weekly deficit becomes explicit unmet_need/debt pressure.
"""
from copy import deepcopy
from datetime import date, timedelta
import random
from .consequence_topology import ConsequenceTopology
from .macro_world import MacroWorld, beijing_2026_macro
from .social_world import SocialWorld
ACTOR_ORDER=("lin_jing","chen_lan","xu_hang"); MONTH_WEEKS=4.345

def _day(w): return (date(2026,3,2)+timedelta(days=7*w)).isoformat()
def _initial_actors(): return {
 "lin_jing":{"cash":38000.,"income":3800.,"expense":3200.,"hours":44,"care":1,"career":.75,"stage":"doctoral","institution":"university_a","debt":0.},
 "chen_lan":{"cash":14600.,"income":2400.,"expense":3600.,"hours":38,"care":3,"career":.72,"stage":"doctoral","institution":"university_a","debt":0.},
 "xu_hang":{"cash":18000.,"income":3000.,"expense":3400.,"hours":42,"care":1,"career":.78,"stage":"doctoral","institution":"university_b","debt":0.}}
def _external_schedule(seed,weeks):
 if weeks<16: raise ValueError("endogenous scouting needs at least 16 weeks")
 rng=random.Random(seed); out=[]
 for actor in ACTOR_ORDER:
  for j,(lo,hi) in enumerate(((max(2,int(.08*weeks)),max(3,int(.30*weeks))),(max(4,int(.38*weeks)),max(5,int(.72*weeks)))),1):
   hi=min(weeks-6,max(lo,hi)); st=rng.randint(lo,hi); out.append({"id":f"family-{actor}-{j}","kind":"family_care_episode","actor":actor,"start_week":st,"end_week":min(weeks,st+rng.randint(5,13)),"extra_hours":rng.choice((2,3,4,5)),"extra_monthly_cost":rng.choice((0,400,800,1200)),"provenance":{"kind":"seeded_exogenous_event","seed":seed}})
 for j in range(max(1,weeks//26)):
  center=min(weeks-1,20+j*26); out.append({"id":f"career-cycle-{j+1}","kind":"career_cycle","week":max(4,min(weeks-1,center+rng.randint(-3,3))),"provenance":{"kind":"seeded_exogenous_event","seed":seed}})
 return sorted(out,key=lambda x:(x.get("week",x.get("start_week",0)),x["id"]))
def _active_family(ev,aid,w):
 rows=[e for e in ev if e["kind"]=="family_care_episode" and e["actor"]==aid and e["start_week"]<=w<e["end_week"]]; return {"hours":sum(e["extra_hours"] for e in rows),"monthly_cost":sum(e["extra_monthly_cost"] for e in rows),"causes":[e["id"] for e in rows]}
def _topology():
 t=ConsequenceTopology(); t.state["resources"].update({"university_a.admin_exception_slot":{"capacity":1.,"allocations":{}},"university_a.priority_recommendation":{"capacity":1.,"allocations":{}},"university_b.priority_recommendation":{"capacity":1.,"allocations":{}}}); return t
def _request_options(aid,a,fam,avail,cycle):
 opts=[]; effective=max(0,a["hours"]-a["care"]-fam["hours"])
 if a["institution"]=="university_a" and fam["hours"]>=3 and avail.get("university_a.admin_exception_slot",0)>=1: opts.append(("admin_exception",1.))
 if aid=="chen_lan" and (a["cash"]<12000 or a["debt"]>0) and effective>=20 and avail.get("mingheng.paid_research_hours",0)>=8: opts.append(("paid_research",8.))
 if cycle and a["stage"]=="doctoral" and a["career"]>=.58:
  rid=f"{a['institution']}.priority_recommendation"
  if avail.get(rid,0)>=1: opts.append(("recommendation",1.))
 if aid=="chen_lan" and a["stage"]=="doctoral" and a["cash"]<9000 and avail.get("university_a.transition_housing",0)>=1: opts.append(("transition_housing",1.))
 return opts
def _resource(a,o): return {"admin_exception":f"{a['institution']}.admin_exception_slot","recommendation":f"{a['institution']}.priority_recommendation","paid_research":"mingheng.paid_research_hours","transition_housing":"university_a.transition_housing"}[o]
def simulate_endogenous_world(seed,weeks=160,macro_state=None):
 macro=MacroWorld(deepcopy(macro_state or beijing_2026_macro())); social=SocialWorld(); topology=_topology(); actors=_initial_actors(); external=_external_schedule(seed,weeks); history=[]; blocked=[]; allocations=[]; lifecycle=[]; hardship=[]; min_cash={k:v["cash"] for k,v in actors.items()}; max_debt={k:0. for k in actors}; last_month=None
 for week in range(weeks):
  when=_day(week); month=when[:7]+"-01"
  if month!=last_month: macro.advance(month); social.update_from_macro(macro); last_month=month
  ss=social.snapshot(); ms=macro.snapshot()["signals"]; cycle=any(e["kind"]=="career_cycle" and e["week"]==week for e in external); avail={rid:topology.resource_available(rid) for rid in topology.state["resources"]}; frozen={}
  for aid in ACTOR_ORDER:
   a=actors[aid]; fam=_active_family(external,aid,week); delta=(a["income"]-a["expense"]-fam["monthly_cost"])/MONTH_WEEKS; projected=a["cash"]+delta
   if projected<0:
    short=-projected; a["cash"]=0.; a["debt"]+=short; n=topology._node("unmet_cash_need",when,actor=aid,payload={"amount":short,"debt_after":a["debt"]}); hardship.append({"week":week+1,"actor":aid,"amount":short,"node":n["id"]})
   else: a["cash"]=projected
   min_cash[aid]=min(min_cash[aid],a["cash"]); max_debt[aid]=max(max_debt[aid],a["debt"])
   if a["institution"] in ss["institutions"]:
    inst=ss["institutions"][a["institution"]]; ai=ms["ai_research_capability"]["value"]; a["career"]=max(0,min(1,a["career"]+.0015*(inst.get("junior_opportunity_capacity",1)-.9)-.0005*max(0,ai-1.4)))
   frozen[aid]={"actor":deepcopy(a),"family":fam,"options":_request_options(aid,a,fam,avail,cycle)}
  urg={"transition_housing":4,"admin_exception":3,"paid_research":2,"recommendation":1}; req=sorted([(urg[o],aid,o,amt,v["family"]["causes"]) for aid,v in frozen.items() for o,amt in v["options"]],key=lambda z:(-z[0],z[1],z[2]))
  for _,aid,o,amt,exts in req:
   rid=_resource(actors[aid],o)
   if topology.resource_available(rid)+1e-9>=amt:
    cs=[]
    for ext in exts: cs.append(topology._node("exogenous_household_event",when,actor=aid,payload={"external_event_id":ext})["id"])
    n=topology.allocate(rid,aid,amt,when,cs); allocations.append({"week":week+1,"actor":aid,"option":o,"resource":rid,"amount":amt,"node":n["id"]})
    if o=="paid_research":
     payment=400*amt; debt_paid=min(actors[aid]["debt"],payment); actors[aid]["debt"]-=debt_paid; actors[aid]["cash"]+=payment-debt_paid
   else: pass
   if o!="paid_research": pass
   if o=="paid_research": max_debt[aid]=max(max_debt[aid],actors[aid]["debt"])
   continue
   
   
   
  else:
   pass
  # Resolve frozen requests that lost capacity after earlier simultaneous winners.
  for _,aid,o,amt,exts in req:
   rid=_resource(actors[aid],o)
   if any(x["week"]==week+1 and x["actor"]==aid and x["option"]==o for x in allocations): continue
   holders=list(topology.state["resources"][rid]["allocations"]); causes=[x["node"] for x in allocations if x["resource"]==rid and x["actor"] in holders and x.get("released") is None]; n=topology._node("option_blocked_by_shared_capacity",when,actor=aid,target=rid,payload={"option":o,"holders":holders},causes=causes[-3:]); blocked.append({"week":week+1,"actor":aid,"option":o,"resource":rid,"holders":holders,"node":n["id"]})
  for rid,ttl in (("university_a.admin_exception_slot",4),("university_a.priority_recommendation",8),("university_b.priority_recommendation",8),("mingheng.paid_research_hours",13)):
   for row in allocations:
    if row["resource"]==rid and row.get("released") is None and week-(row["week"]-1)>=ttl:
     held=topology.state["resources"][rid]["allocations"].get(row["actor"],0)
     if held: row["released"]=topology.release(rid,row["actor"],min(held,row["amount"]),when,[row["node"]])["id"]
  c=actors["chen_lan"]
  if c["stage"]=="doctoral" and week>=36 and c["cash"]>=6000 and c["debt"]==0:
   prior=[x["node"] for x in allocations if x["actor"]=="chen_lan"][-2:]; n=topology.exit_actor("chen_lan",when,"doctoral_stage_completed",prior); c.update(stage="external_worker",institution="mingheng",income=8200.,expense=6000.,hours=40); lifecycle.append({"week":week+1,"actor":"chen_lan","kind":"doctoral_exit","node":n["id"]})
  lin=actors["lin_jing"]
  if lin["stage"]=="doctoral" and week>=104 and lin["career"]<.68:
   n=topology._node("career_path_changed",when,actor="lin_jing",payload={"from":"doctoral","to":"nonacademic_search"}); lin["stage"]="nonacademic_search"; lifecycle.append({"week":week+1,"actor":"lin_jing","kind":"career_path_changed","node":n["id"]})
  if week%4==0 or cycle or (lifecycle and lifecycle[-1]["week"]==week+1): history.append({"week":week+1,"date":when,"actors":deepcopy(actors),"frozen":deepcopy(frozen),"resources":deepcopy(topology.state["resources"])})
 chains=[]
 for b in blocked:
  trace=topology.causal_trace(b["node"]); up=[n for n in trace[:-1] if n["kind"]=="shared_resource_allocated" and n["actor"]!=b["actor"]]
  if up: chains.append({"blocked_actor":b["actor"],"holder_actors":sorted({n["actor"] for n in up}),"resource":b["resource"],"end_week":b["week"],"node":b["node"],"trace_length":len(trace)})
 return {"seed":seed,"weeks":weeks,"external_events":external,"history":history,"allocations":allocations,"blocked":blocked,"lifecycle":lifecycle,"hardship_events":hardship,"cross_actor_chains":chains,"minimum_cash_seen":{k:round(v,2) for k,v in min_cash.items()},"maximum_debt_seen":{k:round(v,2) for k,v in max_debt.items()},"no_negative_cash":min(min_cash.values())>=0,"topology":topology.snapshot(),"status":"endogenous_scouting_noncanonical"}
