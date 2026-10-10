"""Build high-cost ChatGPT replay packets from mined noncanonical histories."""
from copy import deepcopy
from .era_context import context_as_of

REPLAY_RULES = [
 "Treat the simulated person's local knowledge as a hard boundary.",
 "Observed era facts can affect options only after their dates and through plausible information paths.",
 "Future technology/economic waves are uncertain scenario branches; never narrate them as predetermined history.",
 "Large companies, policy, labor markets and technology matter only when they alter prices, jobs, tools, institutions, status or relationships.",
 "Do not insert trend names as exposition decoration.",
 "Do not optimize for drama. Preserve refusals, boring weeks, failed opportunities and path dependence.",
 "Return a decision proposal; canonical mutation must pass the Python world authority.",
]

def replay_packet(run, candidate_week=None):
    history=run.get("history",[])
    if not history: raise ValueError("run has no history")
    if candidate_week is None:
        interesting=[x.get("end_week") for x in run.get("cross_actor_chains",[]) if x.get("end_week")]
        candidate_week=max(interesting) if interesting else history[-1]["week"]
    snap=min(history,key=lambda x:abs(x["week"]-candidate_week))
    day=snap["date"]
    prior_nodes=[n for n in run.get("topology",{}).get("nodes",[]) if n.get("when","")<=day]
    return {"stage":"deep_replay","status":"proposal_noncanonical","world":run.get("spec",{"seed":run.get("seed")}),"target_week":candidate_week,"as_of":day,"frozen_world_view":deepcopy(snap),"causal_history":deepcopy(prior_nodes),"era":context_as_of(day),"rules":list(REPLAY_RULES),"output_schema":{"actor":"string","choice":"string","reason":"string","actions":"list","era_factors_used":"list of observed/scenario ids","uncertainties":"list","counterfactual_rejected":"string"}}

def validate_replay_reply(packet,reply):
    required=set(packet["output_schema"]); missing=required-set(reply)
    if missing: raise ValueError(f"missing replay fields: {sorted(missing)}")
    allowed={x["id"] for x in packet["era"]["observed"]}|{x["id"] for x in packet["era"]["future_scenarios"]}
    bad=set(reply["era_factors_used"])-allowed
    if bad: raise ValueError(f"unknown era factors: {sorted(bad)}")
    return True
