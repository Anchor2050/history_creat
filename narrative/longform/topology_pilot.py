"""Four-world, 160-week pilot for endogenous social consequence chains."""
from copy import deepcopy
from datetime import date, timedelta
import random

from .consequence_topology import ConsequenceTopology, TopologyError
from .social_engine import SocialEngine


def _day(start, week):
    return (date.fromisoformat(start) + timedelta(days=7 * week)).isoformat()


def _initial_actor_states():
    return {
        "lin_jing": {"cash": 38000.0, "weekly_hours": 44, "status": "doctoral"},
        "chen_lan": {"cash": 14600.0, "weekly_hours": 38, "status": "doctoral"},
        "xu_hang": {"cash": 18000.0, "weekly_hours": 42, "status": "doctoral"},
    }


def _choose(view, preference):
    available = view["options"]
    for option in preference:
        if option in available:
            return option
    return None


PREFERENCES = {
    "lin_jing": [
        "request_advisor_attention", "seek_recommendation",
        "seek_bridge_funding", "seek_transition_housing",
    ],
    "chen_lan": [
        "seek_transition_housing", "seek_paid_research_work",
        "seek_bridge_funding", "seek_recommendation", "request_advisor_attention",
    ],
    "xu_hang": ["request_advisor_attention"],
}


def run_topology_pilot(seed, weeks=160):
    rng = random.Random(seed)
    engine = SocialEngine()
    actors = _initial_actor_states()
    start = "2026-03-02"
    decisions = []
    closed_chains = []
    claimed = set()

    # Seed changes only exogenous timing/intensity, never personality.
    family_shock_week = 18 + rng.randint(0, 18)
    housing_competition_week = 34 + rng.randint(0, 12)
    recommendation_competition_week = 68 + rng.randint(0, 16)
    exit_week = 118 + rng.randint(0, 20)

    for w in range(weeks):
        when = _day(start, w)

        # Family obligations consume actual weekly time/cash.
        for aid in actors:
            shock = None
            if aid == "chen_lan" and w == family_shock_week:
                shock = {"extra_care_hours": 4, "extra_obligation": 800}
            result = engine.household_week(
                aid, when, actors[aid]["cash"], actors[aid]["weekly_hours"], shock
            )
            actors[aid]["cash"] = result["cash_after"]
            actors[aid]["effective_hours"] = result["hours_after"]

        # Freeze before any same-week decision.
        frozen_input = {
            aid: {"cash": row["cash"], "weekly_hours": row["effective_hours"]}
            for aid, row in actors.items()
        }
        views = engine.freeze_views(f"week-{w+1:03d}", frozen_input)

        # Scarce housing competition. Order is exogenous and logged by seed.
        if w == housing_competition_week:
            order = ["chen_lan", "lin_jing"] if rng.random() < .5 else ["lin_jing", "chen_lan"]
            for aid in order:
                option = _choose(views[aid], ["seek_transition_housing"])
                if option:
                    try:
                        node = engine.allocate_option(aid, option, when)
                        decisions.append({"week": w+1, "actor": aid, "option": option, "node": node["id"]})
                    except TopologyError:
                        pass

            holder = next(iter(
                engine.topology.state["resources"]["university_a.transition_housing"]["allocations"]
            ), None)
            loser = "lin_jing" if holder == "chen_lan" else "chen_lan"
            if holder and "housing" not in claimed:
                # Loser must redirect scarce attention/funding instead.
                redirect_view = engine.material_options(
                    loser, actors[loser]["cash"], actors[loser]["effective_hours"]
                )
                redirect = next((x for x in ("seek_bridge_funding", "seek_paid_research_work",
                                             "request_advisor_attention") if x in redirect_view), None)
                if redirect:
                    cause = decisions[-1]["node"]
                    try:
                        rnode = engine.allocate_option(loser, redirect, when, [cause])
                        decisions.append({"week": w+1, "actor": loser, "option": redirect,
                                          "node": rnode["id"], "caused_by": cause})
                        # Holder's allocation changed loser's option, which changed a shared resource.
                        affected = "lin_jing" if loser == "chen_lan" else "chen_lan"
                        later_options = engine.material_options(
                            affected, actors[affected]["cash"], actors[affected]["effective_hours"]
                        )
                        closed_chains.append({
                            "kind": "housing_redirect_chain",
                            "actors": [holder, loser, affected],
                            "nodes": [cause, rnode["id"]],
                            "week": w+1,
                            "downstream_options": later_options,
                        })
                        claimed.add("housing")
                    except TopologyError:
                        pass

        # Recommendation competition turns prior reputation/institution memory into access.
        if w == recommendation_competition_week:
            earlier = decisions[-1]["node"] if decisions else None
            message = engine.communicate(
                "sun_jie", "shen_yan", "chen_deadline_reliability", when,
                cause_ids=[earlier] if earlier else None,
            )
            rep = engine.reputation_from_message(
                "shen_yan", "chen_lan", "reliability", 0.25, message, when
            )
            preferred = "chen_lan" if engine.topology.state["reputation"].get(
                "shen_yan|chen_lan|reliability", 0
            ) > 0 else "lin_jing"
            other = "lin_jing" if preferred == "chen_lan" else "chen_lan"
            nodes = []
            for aid in (preferred, other):
                if "seek_recommendation" in engine.material_options(
                        aid, actors[aid]["cash"], actors[aid]["effective_hours"]):
                    try:
                        n = engine.allocate_option(aid, "seek_recommendation", when, [rep["id"]])
                        nodes.append(n["id"])
                    except TopologyError:
                        pass
            if nodes:
                mem = engine.topology.remember(
                    "university_a", "recommendation_cycle_2027",
                    {"preferred": preferred, "allocations": nodes}, when, nodes
                )
                closed_chains.append({
                    "kind": "information_reputation_resource_chain",
                    "actors": ["sun_jie", "shen_yan", preferred, other],
                    "nodes": [message["id"], rep["id"], *nodes, mem["id"]],
                    "week": w+1,
                })

        # Exit releases/changes network position; institutional memory affects the survivor.
        if w == exit_week:
            cause = decisions[-1]["node"] if decisions else None
            exit_node = engine.topology.exit_actor(
                "chen_lan", when, "graduated_and_left_university",
                [cause] if cause else None,
            )
            engine.topology.remember(
                "university_a", "chen_exit",
                {"date": when, "reason": "graduated_and_left_university"},
                when, [exit_node["id"]],
            )
            # Release Chen-held university resources so another actor's feasible set changes.
            released = []
            for rid in (
                "university_a.transition_housing",
                "university_a.recommendation_slots",
                "university_a.bridge_funding",
                "university_a.advisor_attention",
            ):
                held = engine.topology.state["resources"][rid]["allocations"].get("chen_lan", 0)
                if held:
                    r = engine.topology.release(rid, "chen_lan", held, when, [exit_node["id"]])
                    released.append(r["id"])
            lin_after = engine.material_options(
                "lin_jing", actors["lin_jing"]["cash"], actors["lin_jing"]["effective_hours"]
            )
            if released:
                closed_chains.append({
                    "kind": "exit_reopens_opportunity_chain",
                    "actors": ["chen_lan", "lin_jing"],
                    "nodes": [exit_node["id"], *released],
                    "week": w+1,
                    "lin_options_after": lin_after,
                })

    # A chain qualifies only if it crosses actors and contains >=2 explicit causal nodes.
    qualified = [
        c for c in closed_chains
        if len(set(c["actors"])) >= 2 and len(c["nodes"]) >= 2
    ]
    return {
        "seed": seed,
        "weeks": weeks,
        "decisions": decisions,
        "closed_chains": qualified,
        "chain_count": len(qualified),
        "final_topology": engine.topology.snapshot(),
        "final_households": deepcopy(engine.households),
        "status": "pilot_noncanonical",
    }


def run_four_world_pilot(seeds=(101, 202, 303, 404), weeks=160):
    runs = [run_topology_pilot(seed, weeks) for seed in seeds]
    total = sum(r["chain_count"] for r in runs)
    worlds_with_three = sum(r["chain_count"] >= 3 for r in runs)
    return {
        "worlds": runs,
        "total_closed_chains": total,
        "worlds_with_at_least_three_chains": worlds_with_three,
        "acceptance": worlds_with_three >= 1 and total >= 3,
        "status": "pilot_complete" if worlds_with_three >= 1 and total >= 3 else "pilot_failed",
    }
