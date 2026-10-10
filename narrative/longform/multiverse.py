"""Cheap auditable multiverse exploration before expensive literary replay."""
from copy import deepcopy
from datetime import date, timedelta
import math
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


def _bounded(value, lo, hi):
    return min(hi, max(lo, value))


def _inject_seeded_shocks(macro_state, spec):
    """Add auditable exogenous shocks. Stable worlds get no random shocks."""
    if spec["family"] == "stable":
        return macro_state
    rng = random.Random(spec["seed"])
    signals = list(macro_state["signals"])
    n = 3 if spec["family"] == "macro_shocks" else 2 if spec["family"] == "mixed" else 1
    for j in range(n):
        month_offset = rng.randint(4, 35)
        y = 2026 + (2 + month_offset) // 12
        m = (2 + month_offset) % 12 + 1
        signal = rng.choice(signals)
        scale = 0.03 if spec["family"] == "choice_pressure" else 0.08
        delta = rng.uniform(-scale, scale)
        macro_state["scheduled_changes"].append({
            "id": f"{spec['world_id']}-shock-{j+1}",
            "month": f"{y:04d}-{m:02d}-01",
            "signal": signal,
            "delta": delta,
            "public_fact": f"Seeded fictional change affecting {signal}.",
            "provenance": {"kind": "seeded_exogenous_shock", "world_id": spec["world_id"], "seed": spec["seed"]},
        })
    return macro_state


def simulate_world(spec, weeks=160):
    """Run a low-resolution world history with no prose generation.

    This layer records pressures, thresholds and irreversible proxy choices. It is
    a scouting simulation: selected worlds must later be replayed through the
    full character/micro engine before any event becomes canonical fiction.
    """
    macro = MacroWorld(_inject_seeded_shocks(beijing_2026_macro(), spec))
    social = SocialWorld()
    rng = random.Random(spec["seed"] ^ 0x5F3759DF)
    start = "2026-03-02"
    history = []
    actors = {
        "lin_jing": {"career_commitment": 0.75, "cash_strain": 0.25, "ai_adaptation": 0.45},
        "chen_lan": {"career_commitment": 0.72, "cash_strain": 0.55, "ai_adaptation": 0.38},
        "xu_hang": {"career_commitment": 0.78, "cash_strain": 0.30, "ai_adaptation": 0.65},
    }
    last_month = None
    irreversible = []
    delayed_echoes = []

    for week in range(weeks):
        when = _week_date(start, week)
        month = when[:7] + "-01"
        if month != last_month:
            macro.advance(month)
            social.update_from_macro(macro)
            last_month = month
        ms = macro.snapshot()["signals"]
        ua = social.snapshot()["institutions"]["university_a"]
        mh = social.snapshot()["institutions"]["mingheng"]
        housing = social.snapshot()["city"]["young_adult_housing_burden"]

        # Slow adaptation and strain. Randomness is bounded and recorded by seed.
        for aid, a in actors.items():
            ai_gap = max(0.0, ms["ai_research_capability"]["value"] - (1.0 + a["ai_adaptation"]))
            a["ai_adaptation"] = _bounded(a["ai_adaptation"] + 0.0025 + rng.uniform(-0.001, 0.001), 0.0, 1.6)
            housing_push = max(0.0, housing - 1.0) * (0.003 if aid != "chen_lan" else 0.006)
            a["cash_strain"] = _bounded(a["cash_strain"] + housing_push - (0.0015 if aid == "lin_jing" else 0.0008), 0.0, 1.0)
            opportunity = ua["junior_opportunity_capacity"] if aid != "xu_hang" else social.snapshot()["institutions"]["university_b"]["junior_opportunity_capacity"]
            a["career_commitment"] = _bounded(a["career_commitment"] + 0.002 * (opportunity - 0.9) - 0.002 * ai_gap, 0.0, 1.0)

        # Proxy branch points only when constraints cross thresholds. They are not
        # canonical character decisions; they nominate moments for deep replay.
        chen = actors["chen_lan"]
        if not any(x["actor"] == "chen_lan" and x["kind"] == "income_path_pressure" for x in irreversible):
            score = chen["cash_strain"] + 0.30 * (mh["project_capacity"] - 1.0) - 0.20 * mh["automation_substitution"]
            threshold = 0.72 + (rng.random() - 0.5) * (0.10 if spec["family"] in {"choice_pressure", "mixed"} else 0.02)
            if score > threshold:
                irreversible.append({"week": week + 1, "date": when, "actor": "chen_lan", "kind": "income_path_pressure", "score": score, "threshold": threshold})

        for aid in ("lin_jing", "xu_hang"):
            if not any(x["actor"] == aid and x["kind"] == "career_reconsideration" for x in irreversible):
                a = actors[aid]
                if a["career_commitment"] < 0.64:
                    irreversible.append({"week": week + 1, "date": when, "actor": aid, "kind": "career_reconsideration", "score": a["career_commitment"], "threshold": 0.64})

        # Echo: an early branch remains relevant >= 26 weeks later under changed conditions.
        for branch in irreversible:
            age = week + 1 - branch["week"]
            key = (branch["actor"], branch["kind"])
            if age >= 26 and not any((e["actor"], e["source_kind"]) == key for e in delayed_echoes):
                delayed_echoes.append({"week": week + 1, "date": when, "actor": branch["actor"], "source_kind": branch["kind"], "delay_weeks": age})

        if week % 4 == 0 or irreversible and irreversible[-1]["week"] == week + 1:
            history.append({
                "week": week + 1, "date": when,
                "signals": {k: round(v["value"], 5) for k, v in ms.items()},
                "actors": deepcopy(actors),
                "institution": {"university_a": deepcopy(ua), "mingheng": deepcopy(mh)},
            })

    shocks = [s for e in macro.snapshot()["events"] for s in e.get("shocks", [])]
    return {
        "spec": deepcopy(spec), "weeks": weeks, "history": history,
        "irreversible_proxy_points": irreversible, "delayed_echoes": delayed_echoes,
        "macro_shocks": shocks, "final_actors": deepcopy(actors),
        "final_macro": {k: v["value"] for k, v in macro.snapshot()["signals"].items()},
        "social_events": social.snapshot()["events"],
        "status": "scouting_noncanonical",
    }


def score_world(run):
    """Auditable scouting scores; no single 'best story' scalar."""
    branches = len(run["irreversible_proxy_points"])
    echoes = len(run["delayed_echoes"])
    shocks = len(run["macro_shocks"])
    actor_spread = len({x["actor"] for x in run["irreversible_proxy_points"]})
    # Structural tension rewards consequential change but caps event-count gaming.
    tension = min(1.0, 0.22 * branches + 0.12 * shocks)
    causality = min(1.0, 0.32 * echoes + 0.12 * branches)
    ensemble = min(1.0, actor_spread / 3.0)
    change = sum(abs(v - 1.0) for v in run["final_macro"].values()) / len(run["final_macro"])
    historical_pressure = min(1.0, change)
    return {
        "tension": round(tension, 4),
        "causal_echo": round(causality, 4),
        "ensemble_depth": round(ensemble, 4),
        "historical_pressure": round(historical_pressure, 4),
    }


def pareto_candidates(scored, limit=8):
    """Return nondominated worlds, then diversity-fill without scalar collapse."""
    keys = ("tension", "causal_echo", "ensemble_depth", "historical_pressure")
    frontier = []
    for item in scored:
        s = item["scores"]
        dominated = False
        for other in scored:
            if other is item:
                continue
            o = other["scores"]
            if all(o[k] >= s[k] for k in keys) and any(o[k] > s[k] for k in keys):
                dominated = True; break
        if not dominated:
            frontier.append(item)
    frontier.sort(key=lambda x: (x["spec"]["family"], x["spec"]["world_id"]))
    chosen = frontier[:limit]
    if len(chosen) < limit:
        used = {x["spec"]["world_id"] for x in chosen}
        rest = [x for x in scored if x["spec"]["world_id"] not in used]
        rest.sort(key=lambda x: max(x["scores"].values()), reverse=True)
        chosen.extend(rest[:limit-len(chosen)])
    return chosen


def run_multiverse(count=32, weeks=160, master_seed=20261011):
    runs = [simulate_world(spec, weeks) for spec in world_specs(count, master_seed)]
    scored = [{"spec": r["spec"], "scores": score_world(r), "run": r} for r in runs]
    return {"version": 1, "count": count, "weeks": weeks, "master_seed": master_seed,
            "runs": scored, "candidates": pareto_candidates(scored, min(8, count)),
            "status": "scouting_noncanonical_requires_deep_replay"}
