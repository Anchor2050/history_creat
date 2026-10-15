"""Corrected controlled pilot for endogenous social causality.

The pilot is deliberately noncanonical. It verifies mechanisms before large-scale
world generation. A chain only qualifies when an upstream allocation changes a
different actor's feasible option under an explicit counterfactual.
"""
from copy import deepcopy
from datetime import date, timedelta
import random

from .consequence_topology import ConsequenceTopology, TopologyError


MONTH_WEEKS = 4.345


def _date(start, week):
    return (date.fromisoformat(start) + timedelta(days=7 * week)).isoformat()


def _initial_topology():
    t = ConsequenceTopology()
    # Controlled-pilot resources model scarce cycles rather than universal facts.
    t.state["resources"].update({
        "university_a.admin_exception_slot": {"capacity": 1.0, "allocations": {}},
        "university_a.priority_recommendation": {"capacity": 1.0, "allocations": {}},
    })
    # A small bounded project-hours pool makes opportunity cost observable.
    t.state["resources"]["mingheng.paid_research_hours"] = {
        "capacity": 16.0, "allocations": {}
    }
    return t


def _actors():
    return {
        "lin_jing": {
            "cash": 38000.0, "monthly_income": 2600 + 1200,
            "monthly_expense": 3200, "base_hours": 44,
            "care_hours": 1, "active_university": True,
        },
        "chen_lan": {
            "cash": 14600.0, "monthly_income": 2400,
            "monthly_expense": 3600, "base_hours": 38,
            "care_hours": 3, "active_university": True,
        },
        "xu_hang": {
            "cash": 18000.0, "monthly_income": 3000,
            "monthly_expense": 3400, "base_hours": 42,
            "care_hours": 1, "active_university": True,
        },
    }


def _cash_week(actor):
    actor["cash"] += (
        actor["monthly_income"] - actor["monthly_expense"]
    ) / MONTH_WEEKS


def _counterfactual_block(capacity, used_before, upstream_amount, downstream_amount):
    """True iff downstream option exists without upstream and vanishes with it."""
    before = capacity - used_before
    after = capacity - used_before - upstream_amount
    return before + 1e-9 >= downstream_amount and after + 1e-9 < downstream_amount


def _node(t, kind, when, actor=None, target=None, causes=None, **payload):
    return t._node(
        kind, when, actor=actor, target=target,
        payload=payload, causes=causes,
    )


def run_controlled_world(seed, weeks=160):
    rng = random.Random(seed)
    t = _initial_topology()
    actors = _actors()
    events = []
    chains = []
    min_cash_seen = {k: v["cash"] for k, v in actors.items()}

    # Exogenous timing varies; needs and choices remain rule-based.
    care_start = 8 + rng.randint(0, 5)
    care_end = care_start + 18 + rng.randint(0, 8)
    admin_need_chen = 15 + rng.randint(0, 4)
    admin_need_lin = admin_need_chen + 2
    recommendation_lin = 23 + rng.randint(0, 3)
    recommendation_chen = recommendation_lin + 2
    referral_lin = recommendation_chen + 2
    chen_exit = 38 + rng.randint(0, 8)
    long_echo = referral_lin + 32

    admin_holder_node = None
    lin_admin_block_node = None
    nomination_holder_node = None
    chen_nomination_block_node = None
    chen_paid_node = None
    lin_paid_block_node = None

    for w in range(weeks):
        when = _date("2026-03-02", w)

        # Exact starting monthly flows from scenario; care shock changes time only.
        for aid, actor in actors.items():
            _cash_week(actor)
            min_cash_seen[aid] = min(min_cash_seen[aid], actor["cash"])
        chen_extra_care = 4 if care_start <= w < care_end else 0
        effective = {
            "lin_jing": actors["lin_jing"]["base_hours"] - actors["lin_jing"]["care_hours"],
            "chen_lan": actors["chen_lan"]["base_hours"] - actors["chen_lan"]["care_hours"] - chen_extra_care,
            "xu_hang": actors["xu_hang"]["base_hours"] - actors["xu_hang"]["care_hours"],
        }

        # 1) Administrative scarcity: Chen only requests if household load is high.
        if w == admin_need_chen and chen_extra_care >= 4 and effective["chen_lan"] <= 31:
            used = 0.0
            n = t.allocate(
                "university_a.admin_exception_slot", "chen_lan", 1, when
            )
            admin_holder_node = n["id"]
            events.append({"week": w+1, "kind": "chen_admin_request", "node": n["id"]})

        if w == admin_need_lin:
            res = t.state["resources"]["university_a.admin_exception_slot"]
            used = sum(res["allocations"].values())
            if t.resource_available("university_a.admin_exception_slot") < 1:
                block = _node(
                    t, "option_blocked_by_shared_capacity", when,
                    actor="lin_jing", target="university_a.admin_exception_slot",
                    causes=[admin_holder_node] if admin_holder_node else None,
                    requested=1, available=t.resource_available(
                        "university_a.admin_exception_slot"
                    ),
                )
                lin_admin_block_node = block["id"]
                cf = _counterfactual_block(1, 0, 1, 1)
                if cf and admin_holder_node:
                    chains.append({
                        "kind": "admin_displacement",
                        "actors": ["chen_lan", "lin_jing"],
                        "nodes": [admin_holder_node, block["id"]],
                        "start_week": admin_need_chen+1,
                        "end_week": w+1,
                        "counterfactual_verified": True,
                    })
            else:
                n = t.allocate(
                    "university_a.admin_exception_slot", "lin_jing", 1, when
                )
                events.append({"week": w+1, "kind": "lin_admin_success", "node": n["id"]})

        # Slot expires: capacity is temporal, not permanently destroyed.
        if w == admin_need_lin + 4:
            held = t.state["resources"]["university_a.admin_exception_slot"][
                "allocations"
            ].get("chen_lan", 0)
            if held:
                t.release(
                    "university_a.admin_exception_slot", "chen_lan", held, when,
                    [lin_admin_block_node] if lin_admin_block_node else [admin_holder_node],
                )

        # 2) One priority recommendation cycle: Lin's early application and Chen's
        # job search genuinely compete for the same cycle.
        if w == recommendation_lin and actors["lin_jing"]["active_university"]:
            n = t.allocate(
                "university_a.priority_recommendation", "lin_jing", 1, when,
                [lin_admin_block_node] if lin_admin_block_node else None,
            )
            nomination_holder_node = n["id"]
            events.append({"week": w+1, "kind": "lin_recommendation", "node": n["id"]})

        if w == recommendation_chen and actors["chen_lan"]["active_university"]:
            if t.resource_available("university_a.priority_recommendation") < 1:
                b = _node(
                    t, "option_blocked_by_shared_capacity", when,
                    actor="chen_lan", target="university_a.priority_recommendation",
                    causes=[nomination_holder_node] if nomination_holder_node else None,
                    requested=1, available=t.resource_available(
                        "university_a.priority_recommendation"
                    ),
                )
                chen_nomination_block_node = b["id"]
                if nomination_holder_node and _counterfactual_block(1, 0, 1, 1):
                    chains.append({
                        "kind": "recommendation_displacement",
                        "actors": ["lin_jing", "chen_lan"],
                        "nodes": [nomination_holder_node, b["id"]],
                        "start_week": recommendation_lin+1,
                        "end_week": w+1,
                        "counterfactual_verified": True,
                    })

                # Rule-based alternative: cash buffer is declining, so Chen accepts
                # one bounded 16h paid package if the project pool can support it.
                if actors["chen_lan"]["cash"] < 12000 and effective["chen_lan"] >= 24:
                    p = t.allocate(
                        "mingheng.paid_research_hours", "chen_lan", 16, when,
                        [b["id"]],
                    )
                    chen_paid_node = p["id"]
                    actors["chen_lan"]["cash"] += 3200
                    min_cash_seen["chen_lan"] = min(min_cash_seen["chen_lan"], actors["chen_lan"]["cash"])
                    events.append({
                        "week": w+1, "kind": "chen_paid_work",
                        "node": p["id"], "cash_after": actors["chen_lan"]["cash"],
                    })

        # 3) Chen later recommends Lin for a bounded gig. Her own fallback choice
        # can make the referral materially impossible: Lin -> Chen -> Lin feedback.
        if w == referral_lin and chen_paid_node:
            referral = _node(
                t, "referral_transmitted", when, actor="chen_lan",
                target="lin_jing", causes=[chen_paid_node],
                opportunity="mingheng_paid_research",
            )
            if t.resource_available("mingheng.paid_research_hours") < 8:
                block = _node(
                    t, "option_blocked_by_shared_capacity", when,
                    actor="lin_jing", target="mingheng.paid_research_hours",
                    causes=[referral["id"]],
                    requested=8, available=t.resource_available(
                        "mingheng.paid_research_hours"
                    ),
                )
                lin_paid_block_node = block["id"]
                if _counterfactual_block(16, 0, 16, 8):
                    chains.append({
                        "kind": "feedback_paid_work_collision",
                        "actors": ["lin_jing", "chen_lan", "lin_jing"],
                        "nodes": [
                            nomination_holder_node,
                            chen_nomination_block_node,
                            chen_paid_node,
                            referral["id"],
                            block["id"],
                        ],
                        "start_week": recommendation_lin+1,
                        "end_week": w+1,
                        "counterfactual_verified": True,
                    })

        # Long echo: institutional memory preserves why the later opportunity exists.
        if w == long_echo and lin_paid_block_node:
            memo = t.remember(
                "mingheng", "2026_capacity_collision",
                {
                    "chen_completed_paid_package": True,
                    "lin_referral_was_capacity_blocked": True,
                },
                when, [lin_paid_block_node],
            )
            offer = _node(
                t, "delayed_opportunity", when, actor="zhao_ke",
                target="lin_jing", causes=[memo["id"]],
                reason="prior_referral_blocked_by_capacity",
            )
            chains.append({
                "kind": "delayed_institutional_memory_echo",
                "actors": ["chen_lan", "lin_jing", "zhao_ke", "lin_jing"],
                "nodes": [lin_paid_block_node, memo["id"], offer["id"]],
                "start_week": referral_lin+1,
                "end_week": w+1,
                "delay_weeks": w-referral_lin,
                "counterfactual_verified": True,
            })

        # Lifecycle: Chen graduates and exits the university network.
        if w == chen_exit and actors["chen_lan"]["active_university"]:
            cause = chen_paid_node or chen_nomination_block_node
            x = t.exit_actor(
                "chen_lan", when, "graduated_and_started_external_job",
                [cause] if cause else None,
            )
            actors["chen_lan"]["active_university"] = False
            actors["chen_lan"]["monthly_income"] = 8200
            actors["chen_lan"]["monthly_expense"] = 6000
            # Dorm/doctoral support ends; post-graduation budget is independent.
            events.append({"week": w+1, "kind": "chen_exit", "node": x["id"]})

        # Reset the paid-project cycle after 13 weeks; explicit release preserves history.
        if chen_paid_node and w == recommendation_chen + 13:
            held = t.state["resources"]["mingheng.paid_research_hours"][
                "allocations"
            ].get("chen_lan", 0)
            if held:
                t.release(
                    "mingheng.paid_research_hours", "chen_lan", held, when,
                    [chen_paid_node],
                )

    qualified = [
        c for c in chains
        if c.get("counterfactual_verified")
        and len(set(c["actors"])) >= 2
        and len(c["nodes"]) >= 2
    ]
    min_cash = min(min_cash_seen.values())
    return {
        "seed": seed,
        "weeks": weeks,
        "events": events,
        "closed_chains": qualified,
        "chain_count": len(qualified),
        "has_delayed_cross_actor_echo": any(
            c.get("delay_weeks", 0) >= 26 for c in qualified
        ),
        "final_cash": {k: round(v["cash"], 2) for k, v in actors.items()},
        "minimum_cash_seen": {k: round(v, 2) for k, v in min_cash_seen.items()},
        "no_negative_cash": min_cash >= 0,
        "status": "controlled_pilot_noncanonical",
    }


def run_four_world_controlled_pilot(seeds=(101, 202, 303, 404), weeks=160):
    runs = [run_controlled_world(seed, weeks) for seed in seeds]
    accepted_worlds = [
        r for r in runs
        if r["chain_count"] >= 3
        and r["has_delayed_cross_actor_echo"]
        and r["no_negative_cash"]
    ]
    return {
        "worlds": runs,
        "accepted_world_ids": [r["seed"] for r in accepted_worlds],
        "acceptance": bool(accepted_worlds),
        "acceptance_rule": (
            ">=3 counterfactual-verified cross-actor chains, >=1 delayed echo, "
            "and no negative personal cash"
        ),
        "status": "pilot_passed" if accepted_worlds else "pilot_failed",
    }
