"""Endogenous long-horizon social simulator for multiverse scouting.

This is still noncanonical. It removes hand-scheduled character collisions:
external events are seeded and logged; household, institution, cash and lifecycle
states evolve; actor requests are deterministic responses to their frozen state;
scarcity resolves simultaneous requests and records the resulting causal graph.
"""
from copy import deepcopy
from datetime import date, timedelta
import random

from .consequence_topology import ConsequenceTopology, TopologyError
from .macro_world import MacroWorld, beijing_2026_macro
from .social_world import SocialWorld


ACTOR_ORDER = ("lin_jing", "chen_lan", "xu_hang")
MONTH_WEEKS = 4.345


def _day(week):
    return (date(2026, 3, 2) + timedelta(days=7 * week)).isoformat()


def _initial_actors():
    return {
        "lin_jing": {"cash": 38000.0, "income": 3800.0, "expense": 3200.0, "hours": 44, "care": 1,
                     "career": 0.75, "stage": "doctoral", "institution": "university_a", "age": 28},
        "chen_lan": {"cash": 14600.0, "income": 2400.0, "expense": 3600.0, "hours": 38, "care": 3,
                     "career": 0.72, "stage": "doctoral", "institution": "university_a", "age": 31},
        "xu_hang": {"cash": 18000.0, "income": 3000.0, "expense": 3400.0, "hours": 42, "care": 1,
                    "career": 0.78, "stage": "doctoral", "institution": "university_b", "age": 27},
    }


def _external_schedule(seed, weeks):
    """Only external timing is random; every draw is returned for replay."""
    rng = random.Random(seed)
    events = []
    for actor in ACTOR_ORDER:
        # At most two bounded family-care episodes over 160 weeks.
        for j in range(2):
            start = rng.randint(8 + j * 55, min(weeks - 12, 48 + j * 65))
            duration = rng.randint(5, 13)
            extra_hours = rng.choice((2, 3, 4, 5))
            extra_cost = rng.choice((0, 400, 800, 1200))
            events.append({"id": f"family-{actor}-{j+1}", "kind": "family_care_episode", "actor": actor,
                           "start_week": start, "end_week": min(weeks, start + duration),
                           "extra_hours": extra_hours, "extra_monthly_cost": extra_cost,
                           "provenance": {"kind": "seeded_exogenous_event", "seed": seed}})
    # Institutional hiring/recommendation cycles are public external opportunities.
    for j in range(5):
        events.append({"id": f"career-cycle-{j+1}", "kind": "career_cycle",
                       "week": 24 + j * 26 + rng.randint(-3, 3),
                       "provenance": {"kind": "seeded_exogenous_event", "seed": seed}})
    return sorted(events, key=lambda x: (x.get("week", x.get("start_week", 0)), x["id"]))


def _active_family(events, actor, week):
    rows = [e for e in events if e["kind"] == "family_care_episode" and e["actor"] == actor
            and e["start_week"] <= week < e["end_week"]]
    return {"hours": sum(e["extra_hours"] for e in rows),
            "monthly_cost": sum(e["extra_monthly_cost"] for e in rows),
            "causes": [e["id"] for e in rows]}


def _topology():
    t = ConsequenceTopology()
    t.state["resources"].update({
        "university_a.admin_exception_slot": {"capacity": 1.0, "allocations": {}},
        "university_a.priority_recommendation": {"capacity": 1.0, "allocations": {}},
        "university_b.priority_recommendation": {"capacity": 1.0, "allocations": {}},
    })
    return t


def _request_options(actor_id, actor, family, social, topology, career_cycle):
    """Deterministic needs from frozen material state; no personality random walk."""
    opts = []
    effective_hours = max(0, actor["hours"] - actor["care"] - family["hours"])
    if actor["institution"] == "university_a" and family["hours"] >= 3 and topology.resource_available("university_a.admin_exception_slot") >= 1:
        opts.append(("admin_exception", 1.0))
    if actor_id == "chen_lan" and actor["cash"] < 12000 and effective_hours >= 20 and topology.resource_available("mingheng.paid_research_hours") >= 8:
        opts.append(("paid_research", 8.0))
    if career_cycle and actor["stage"] == "doctoral" and actor["career"] >= 0.58:
        rid = f"{actor['institution']}.priority_recommendation"
        if rid in topology.state["resources"] and topology.resource_available(rid) >= 1:
            opts.append(("recommendation", 1.0))
    if actor_id == "chen_lan" and actor["stage"] == "doctoral" and actor["cash"] < 9000 and topology.resource_available("university_a.transition_housing") >= 1:
        opts.append(("transition_housing", 1.0))
    return opts


def _resource(actor, option):
    if option == "admin_exception": return f"{actor['institution']}.admin_exception_slot"
    if option == "recommendation": return f"{actor['institution']}.priority_recommendation"
    if option == "paid_research": return "mingheng.paid_research_hours"
    if option == "transition_housing": return "university_a.transition_housing"
    raise ValueError(option)


def simulate_endogenous_world(seed, weeks=160, macro_state=None):
    macro = MacroWorld(deepcopy(macro_state or beijing_2026_macro()))
    social = SocialWorld()
    topology = _topology()
    actors = _initial_actors()
    external = _external_schedule(seed, weeks)
    history, blocked, allocations, lifecycle = [], [], [], []
    min_cash = {k: v["cash"] for k, v in actors.items()}
    last_month = None

    for week in range(weeks):
        when = _day(week)
        month = when[:7] + "-01"
        if month != last_month:
            macro.advance(month); social.update_from_macro(macro); last_month = month
        ss = social.snapshot(); ms = macro.snapshot()["signals"]
        career_cycle = any(e["kind"] == "career_cycle" and e["week"] == week for e in external)

        # First evolve everyone, then freeze all requests.
        frozen = {}
        for aid in ACTOR_ORDER:
            a = actors[aid]
            fam = _active_family(external, aid, week)
            a["cash"] += (a["income"] - a["expense"] - fam["monthly_cost"]) / MONTH_WEEKS
            min_cash[aid] = min(min_cash[aid], a["cash"])
            inst = ss["institutions"][a["institution"]]
            ai = ms["ai_research_capability"]["value"]
            a["career"] = max(0.0, min(1.0, a["career"] + 0.0015 * (inst["junior_opportunity_capacity"] - .9) - 0.0005 * max(0, ai - 1.4)))
            frozen[aid] = {"actor": deepcopy(a), "family": fam,
                           "options": _request_options(aid, a, fam, ss, topology, career_cycle)}

        # Simultaneous requests: priority is material urgency, then stable actor id.
        requests = []
        urgency = {"transition_housing": 4, "admin_exception": 3, "paid_research": 2, "recommendation": 1}
        for aid, view in frozen.items():
            for option, amount in view["options"]:
                requests.append((urgency[option], aid, option, amount, view["family"]["causes"]))
        requests.sort(key=lambda x: (-x[0], x[1], x[2]))
        for _, aid, option, amount, exogenous_causes in requests:
            rid = _resource(actors[aid], option)
            if topology.resource_available(rid) + 1e-9 >= amount:
                cause_nodes = []
                for ext in exogenous_causes:
                    n = topology._node("exogenous_household_event", when, actor=aid, payload={"external_event_id": ext})
                    cause_nodes.append(n["id"])
                n = topology.allocate(rid, aid, amount, when, cause_nodes)
                allocations.append({"week": week+1, "actor": aid, "option": option, "resource": rid, "node": n["id"]})
                if option == "paid_research": actors[aid]["cash"] += 400 * amount
            else:
                holders = list(topology.state["resources"][rid]["allocations"])
                causes = [x["node"] for x in allocations if x["resource"] == rid and x["actor"] in holders]
                n = topology._node("option_blocked_by_shared_capacity", when, actor=aid, target=rid,
                                   payload={"option": option, "holders": holders}, causes=causes[-3:])
                blocked.append({"week": week+1, "actor": aid, "option": option, "resource": rid,
                                "holders": holders, "node": n["id"]})

        # Temporal capacities expire without erasing history.
        for rid, ttl in (("university_a.admin_exception_slot", 4), ("university_a.priority_recommendation", 8),
                         ("university_b.priority_recommendation", 8), ("mingheng.paid_research_hours", 13)):
            for row in list(allocations):
                if row["resource"] == rid and row.get("released") is None and week - (row["week"]-1) >= ttl:
                    held = topology.state["resources"][rid]["allocations"].get(row["actor"], 0)
                    if held:
                        rel = topology.release(rid, row["actor"], min(held, 8 if rid == "mingheng.paid_research_hours" else 1), when, [row["node"]])
                        row["released"] = rel["id"]

        # Lifecycle thresholds arise from accumulated state, not scheduled character events.
        chen = actors["chen_lan"]
        if chen["stage"] == "doctoral" and week >= 36 and chen["cash"] >= 6000:
            prior = [x["node"] for x in allocations if x["actor"] == "chen_lan"][-2:]
            n = topology.exit_actor("chen_lan", when, "doctoral_stage_completed", prior)
            chen.update(stage="external_worker", institution="mingheng", income=8200.0, expense=6000.0, hours=40)
            lifecycle.append({"week": week+1, "actor": "chen_lan", "kind": "doctoral_exit", "node": n["id"]})
        lin = actors["lin_jing"]
        if lin["stage"] == "doctoral" and week >= 104 and lin["career"] < .68:
            n = topology._node("career_path_changed", when, actor="lin_jing", payload={"from": "doctoral", "to": "nonacademic_search"})
            lin["stage"] = "nonacademic_search"; lifecycle.append({"week": week+1, "actor": "lin_jing", "kind": "career_path_changed", "node": n["id"]})

        if week % 4 == 0 or career_cycle or (lifecycle and lifecycle[-1]["week"] == week+1):
            history.append({"week": week+1, "date": when, "actors": deepcopy(actors),
                            "frozen": deepcopy(frozen), "resources": deepcopy(topology.state["resources"])})

    # A real cross-actor chain requires an allocation by one actor to be an ancestor of another actor's block.
    chains = []
    for b in blocked:
        trace = topology.causal_trace(b["node"])
        upstream = [n for n in trace[:-1] if n["kind"] == "shared_resource_allocated" and n["actor"] != b["actor"]]
        if upstream:
            chains.append({"blocked_actor": b["actor"], "holder_actors": sorted({n["actor"] for n in upstream}),
                           "resource": b["resource"], "end_week": b["week"], "node": b["node"],
                           "trace_length": len(trace)})
    return {"seed": seed, "weeks": weeks, "external_events": external, "history": history,
            "allocations": allocations, "blocked": blocked, "lifecycle": lifecycle,
            "cross_actor_chains": chains, "minimum_cash_seen": {k: round(v, 2) for k, v in min_cash.items()},
            "no_negative_cash": min(min_cash.values()) >= 0, "topology": topology.snapshot(),
            "status": "endogenous_scouting_noncanonical"}
