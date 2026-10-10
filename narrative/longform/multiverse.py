"""Auditable 160-week multiverse scouting before expensive literary replay.

Randomness belongs to logged exogenous conditions. Actor state transitions are
deterministic functions of history. Ambiguous choices are nominated for later
ChatGPT replay rather than settled by weekly random thresholds.
"""
from copy import deepcopy
from datetime import date, timedelta
import random

from .macro_world import MacroWorld, beijing_2026_macro
from .social_world import SocialWorld


WORLD_FAMILIES = ("stable", "macro_shocks", "choice_pressure", "mixed")


def world_specs(count=32, master_seed=20261011):
    if count <= 0:
        raise ValueError("count must be positive")
    rng = random.Random(master_seed)
    specs = []
    for i in range(count):
        family = WORLD_FAMILIES[(i * len(WORLD_FAMILIES)) // count] if count >= 4 else WORLD_FAMILIES[i % 4]
        specs.append({"world_id": f"world-{i+1:03d}", "seed": rng.randrange(1, 2**31), "family": family})
    return specs


def _week_date(start, week):
    return (date.fromisoformat(start) + timedelta(days=7 * week)).isoformat()


def _month_after(start_month, offset):
    y, m = map(int, start_month.split("-")[:2])
    index = y * 12 + (m - 1) + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}-01"


def _bounded(value, lo, hi):
    return min(hi, max(lo, value))


def _inject_seeded_shocks(macro_state, spec):
    """Vary only logged external conditions; stable/choice worlds share baseline."""
    if spec["family"] not in {"macro_shocks", "mixed"}:
        return macro_state
    rng = random.Random(spec["seed"])
    signals = list(macro_state["signals"])
    n = 3 if spec["family"] == "macro_shocks" else 2
    for j in range(n):
        month_offset = rng.randint(4, 35)
        signal = rng.choice(signals)
        delta = rng.uniform(-0.08, 0.08)
        macro_state["scheduled_changes"].append({
            "id": f"{spec['world_id']}-shock-{j+1}",
            "month": _month_after("2026-03-01", month_offset),
            "signal": signal,
            "delta": delta,
            "public_fact": f"Seeded fictional change affecting {signal}.",
            "provenance": {"kind": "seeded_exogenous_shock", "world_id": spec["world_id"], "seed": spec["seed"]},
        })
    return macro_state


def _choice_profile(spec):
    """One logged world-level ambiguity profile, never redrawn each week."""
    base = {"chen_income": 0.72, "lin_career": 0.64, "xu_career": 0.64}
    if spec["family"] not in {"choice_pressure", "mixed"}:
        return base
    rng = random.Random(spec["seed"] ^ 0xC0FFEE)
    return {
        "chen_income": base["chen_income"] + rng.uniform(-0.05, 0.05),
        "lin_career": base["lin_career"] + rng.uniform(-0.035, 0.035),
        "xu_career": base["xu_career"] + rng.uniform(-0.035, 0.035),
    }


def simulate_world(spec, weeks=160):
    """Run deterministic actor adaptation under logged exogenous conditions."""
    macro = MacroWorld(_inject_seeded_shocks(beijing_2026_macro(), spec))
    social = SocialWorld()
    thresholds = _choice_profile(spec)
    start = "2026-03-02"
    history = []
    actors = {
        "lin_jing": {"career_commitment": 0.75, "cash_strain": 0.25, "ai_adaptation": 0.45},
        "chen_lan": {"career_commitment": 0.72, "cash_strain": 0.55, "ai_adaptation": 0.38},
        "xu_hang": {"career_commitment": 0.78, "cash_strain": 0.30, "ai_adaptation": 0.65},
    }
    last_month = None
    decision_nodes = []
    delayed_echoes = []

    for week in range(weeks):
        when = _week_date(start, week)
        month = when[:7] + "-01"
        if month != last_month:
            macro.advance(month)
            social.update_from_macro(macro)
            last_month = month
        ms = macro.snapshot()["signals"]
        ss = social.snapshot()
        ua = ss["institutions"]["university_a"]
        ub = ss["institutions"]["university_b"]
        mh = ss["institutions"]["mingheng"]
        housing = ss["city"]["young_adult_housing_burden"]

        # Deterministic adaptation. External conditions may vary; personality does not jitter.
        for aid, a in actors.items():
            ai_gap = max(0.0, ms["ai_research_capability"]["value"] - (1.0 + a["ai_adaptation"]))
            a["ai_adaptation"] = _bounded(a["ai_adaptation"] + 0.0025 + 0.0008 * max(0.0, ai_gap), 0.0, 1.6)
            housing_push = max(0.0, housing - 1.0) * (0.003 if aid != "chen_lan" else 0.006)
            recovery = 0.0015 if aid == "lin_jing" else 0.0008
            a["cash_strain"] = _bounded(a["cash_strain"] + housing_push - recovery, 0.0, 1.0)
            opportunity = ub["junior_opportunity_capacity"] if aid == "xu_hang" else ua["junior_opportunity_capacity"]
            a["career_commitment"] = _bounded(a["career_commitment"] + 0.002 * (opportunity - 0.9) - 0.002 * ai_gap, 0.0, 1.0)

        # These are replay nominations, not canonical choices.
        chen = actors["chen_lan"]
        if not any(x["actor"] == "chen_lan" and x["kind"] == "income_path_ambiguity" for x in decision_nodes):
            score = chen["cash_strain"] + 0.30 * (mh["project_capacity"] - 1.0) - 0.20 * mh["automation_substitution"]
            if score > thresholds["chen_income"]:
                decision_nodes.append({"week": week + 1, "date": when, "actor": "chen_lan", "kind": "income_path_ambiguity", "score": score, "threshold": thresholds["chen_income"]})

        for aid in ("lin_jing", "xu_hang"):
            kind = "career_reconsideration_ambiguity"
            if not any(x["actor"] == aid and x["kind"] == kind for x in decision_nodes):
                threshold = thresholds["lin_career" if aid == "lin_jing" else "xu_career"]
                if actors[aid]["career_commitment"] < threshold:
                    decision_nodes.append({"week": week + 1, "date": when, "actor": aid, "kind": kind, "score": actors[aid]["career_commitment"], "threshold": threshold})

        for branch in decision_nodes:
            age = week + 1 - branch["week"]
            key = (branch["actor"], branch["kind"])
            if age >= 26 and not any((e["actor"], e["source_kind"]) == key for e in delayed_echoes):
                delayed_echoes.append({"week": week + 1, "date": when, "actor": branch["actor"], "source_kind": branch["kind"], "delay_weeks": age})

        if week % 4 == 0 or (decision_nodes and decision_nodes[-1]["week"] == week + 1):
            history.append({
                "week": week + 1, "date": when,
                "signals": {k: round(v["value"], 5) for k, v in ms.items()},
                "actors": deepcopy(actors),
                "institution": {"university_a": deepcopy(ua), "university_b": deepcopy(ub), "mingheng": deepcopy(mh)},
            })

    shocks = [s for e in macro.snapshot()["events"] for s in e.get("shocks", [])]
    return {
        "spec": deepcopy(spec), "weeks": weeks, "history": history,
        "choice_profile": thresholds,
        "decision_replay_nodes": decision_nodes, "delayed_echoes": delayed_echoes,
        "macro_shocks": shocks, "final_actors": deepcopy(actors),
        "final_macro": {k: v["value"] for k, v in macro.snapshot()["signals"].items()},
        "social_events": social.snapshot()["events"],
        "status": "scouting_noncanonical",
    }


def score_world(run):
    """Structural features only; no single drama score."""
    branches = len(run["decision_replay_nodes"])
    echoes = len(run["delayed_echoes"])
    shocks = len(run["macro_shocks"])
    actor_spread = len({x["actor"] for x in run["decision_replay_nodes"]})
    tension = min(1.0, 0.22 * branches + 0.12 * shocks)
    causality = min(1.0, 0.32 * echoes + 0.12 * branches)
    ensemble = min(1.0, actor_spread / 3.0)
    change = sum(abs(v - 1.0) for v in run["final_macro"].values()) / len(run["final_macro"])
    return {"tension": round(tension, 4), "causal_echo": round(causality, 4), "ensemble_depth": round(ensemble, 4), "historical_pressure": round(min(1.0, change), 4)}


def pareto_candidates(scored, limit=8):
    keys = ("tension", "causal_echo", "ensemble_depth", "historical_pressure")
    frontier = []
    for item in scored:
        s = item["scores"]
        dominated = any(
            other is not item and all(other["scores"][k] >= s[k] for k in keys)
            and any(other["scores"][k] > s[k] for k in keys)
            for other in scored
        )
        if not dominated:
            frontier.append(item)
    frontier.sort(key=lambda x: (x["spec"]["family"], x["spec"]["world_id"]))
    chosen = frontier[:limit]
    if len(chosen) < limit:
        used = {x["spec"]["world_id"] for x in chosen}
        rest = [x for x in scored if x["spec"]["world_id"] not in used]
        # Diversity fill rotates families before using feature strength as tie break.
        rest.sort(key=lambda x: (x["spec"]["family"], -max(x["scores"].values()), x["spec"]["world_id"]))
        chosen.extend(rest[:limit-len(chosen)])
    return chosen


def run_multiverse(count=32, weeks=160, master_seed=20261011):
    runs = [simulate_world(spec, weeks) for spec in world_specs(count, master_seed)]
    scored = [{"spec": r["spec"], "scores": score_world(r), "run": r} for r in runs]
    return {"version": 2, "count": count, "weeks": weeks, "master_seed": master_seed,
            "runs": scored, "candidates": pareto_candidates(scored, min(8, count)),
            "status": "scouting_noncanonical_requires_deep_replay"}
