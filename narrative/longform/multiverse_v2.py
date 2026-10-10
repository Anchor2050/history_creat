"""Threshold-rich noncanonical scouting for long-horizon worlds.

This is deliberately cheaper than literary replay. It creates auditable candidate
moments; it never makes them canonical character decisions.
"""
from copy import deepcopy
from datetime import date, timedelta
import random

from .macro_world import MacroWorld, beijing_2026_macro
from .social_world import SocialWorld
from .multiverse import world_specs, _inject_seeded_shocks, _bounded


def _when(start, week):
    return (date.fromisoformat(start) + timedelta(days=7 * week)).isoformat()


def simulate_world_v2(spec, weeks=160):
    macro = MacroWorld(_inject_seeded_shocks(beijing_2026_macro(), spec))
    social = SocialWorld()
    rng = random.Random(spec["seed"] ^ 0xA17E5)
    actors = {
        "lin_jing": {"career": .78, "cash_strain": .22, "ai_adaptation": .45},
        "chen_lan": {"career": .72, "cash_strain": .58, "ai_adaptation": .38},
        "xu_hang": {"career": .80, "cash_strain": .28, "ai_adaptation": .65},
        "wu_cheng": {"capacity": .78}, "shen_yan": {"capacity": .72},
        "gu_wei": {"capacity": .80}, "zhao_ke": {"capacity": .76},
        "sun_jie": {"capacity": .82},
    }
    dispositions = {a: rng.uniform(-.06, .06) for a in actors}
    events, echoes, seen, echo_seen = [], [], set(), set()
    last_month = None

    def nominate(week, when, actor, kind, score, threshold, causes):
        key = (actor, kind)
        if key in seen or score < threshold:
            return
        seen.add(key)
        events.append({"week": week, "date": when, "actor": actor, "kind": kind,
                       "score": round(score, 6), "threshold": threshold,
                       "causes": list(causes), "status": "proxy_noncanonical"})

    for wi in range(weeks):
        week, when = wi + 1, _when("2026-03-02", wi)
        month = when[:7] + "-01"
        if month != last_month:
            macro.advance(month); social.update_from_macro(macro); last_month = month
        ms = {k: v["value"] for k, v in macro.snapshot()["signals"].items()}
        ss = social.snapshot(); ua = ss["institutions"]["university_a"]
        ub = ss["institutions"]["university_b"]; mh = ss["institutions"]["mingheng"]
        housing = ss["city"]["young_adult_housing_burden"]

        for aid in ("lin_jing", "chen_lan", "xu_hang"):
            a = actors[aid]
            gap = max(0., ms["ai_research_capability"] - (1. + a["ai_adaptation"]))
            a["ai_adaptation"] = _bounded(a["ai_adaptation"] + .003 + rng.uniform(-.0012, .0012), 0., 1.6)
            transition = {"lin_jing": .0008, "chen_lan": .0020, "xu_hang": .0007}[aid]
            relief = .001 if aid == "lin_jing" else 0.
            a["cash_strain"] = _bounded(a["cash_strain"] + transition + .004 * max(0., housing - 1.) - relief, 0., 1.)
            opportunity = ua["junior_opportunity_capacity"] if aid != "xu_hang" else ub["junior_opportunity_capacity"]
            a["career"] = _bounded(a["career"] + .0012 * (opportunity - 1.) - .0018 * gap + dispositions[aid] / 500., 0., 1.)

        for aid in ("wu_cheng", "shen_yan", "gu_wei", "sun_jie"):
            actors[aid]["capacity"] = _bounded(actors[aid]["capacity"] + .0008 * (ms["university_discretionary_budget"] - 1.) + dispositions[aid] / 1200., .25, 1.)
        actors["zhao_ke"]["capacity"] = _bounded(actors["zhao_ke"]["capacity"] + .001 * (mh["project_capacity"] - 1.) + dispositions["zhao_ke"] / 1200., .25, 1.2)

        chen = actors["chen_lan"]
        nominate(week, when, "chen_lan", "income_path_pressure",
                 .65 * chen["cash_strain"] + .22 * mh["project_capacity"] + .13 * (1. - ua["junior_opportunity_capacity"]), .64,
                 ["cash_strain", "project_capacity", "junior_opportunity_capacity"])
        nominate(week, when, "chen_lan", "housing_transition",
                 .75 * chen["cash_strain"] + .25 * housing, .69, ["cash_strain", "housing"])
        for aid in ("lin_jing", "chen_lan", "xu_hang"):
            a = actors[aid]
            nominate(week, when, aid, "career_reconsideration", 1. - a["career"], .28 if aid == "chen_lan" else .25,
                     ["career_commitment", "job_market", "ai_gap"])
            ai_score = max(0., ms["ai_research_capability"] - (1. + a["ai_adaptation"])) + .35 * mh["automation_substitution"]
            nominate(week, when, aid, "ai_workflow_redefinition", ai_score, .20, ["ai_capability", "adaptation", "automation_substitution"])
        nominate(week, when, "shen_yan", "scarce_recommendation_capacity", 1. - actors["shen_yan"]["capacity"], .30, ["university_budget"])
        nominate(week, when, "wu_cheng", "scarce_supervision_capacity", 1. - actors["wu_cheng"]["capacity"], .28, ["university_budget"])
        nominate(week, when, "gu_wei", "method_role_redefinition", mh["automation_substitution"] + .3 * max(0., ms["ai_research_capability"] - 1.45), .30, ["ai_capability"])
        nominate(week, when, "zhao_ke", "service_model_redefinition", mh["automation_substitution"] + .5 * max(0., mh["project_capacity"] - 1.), .28, ["automation_substitution", "project_capacity"])
        nominate(week, when, "sun_jie", "admin_bottleneck", 1. - actors["sun_jie"]["capacity"], .24, ["university_budget"])

        for ev in events:
            key = (ev["actor"], ev["kind"])
            if week - ev["week"] >= 26 and key not in echo_seen:
                echo_seen.add(key)
                echoes.append({"week": week, "date": when, "actor": ev["actor"],
                               "source_kind": ev["kind"], "delay_weeks": week - ev["week"],
                               "status": "echo_candidate_noncanonical"})

    shocks = [s for e in macro.snapshot()["events"] for s in e.get("shocks", [])]
    return {"spec": deepcopy(spec), "weeks": weeks, "proxy_points": events,
            "delayed_echoes": echoes, "macro_shocks": shocks, "final_actors": deepcopy(actors),
            "final_macro": {k: v["value"] for k, v in macro.snapshot()["signals"].items()},
            "status": "scouting_noncanonical_requires_deep_replay"}


def score_world_v2(run):
    points = run["proxy_points"]
    actors = len({p["actor"] for p in points})
    late = sum(p["week"] >= 80 for p in points)
    return {"consequence_density": min(1., len(points) / 8.),
            "ensemble_reach": min(1., actors / 6.),
            "delayed_echo": min(1., len(run["delayed_echoes"]) / 6.),
            "long_arc": min(1., late / 4.),
            "exogenous_change": min(1., len(run["macro_shocks"]) / 5.)}


def run_multiverse_v2(count=32, weeks=160, master_seed=20261011):
    runs = [simulate_world_v2(s, weeks) for s in world_specs(count, master_seed)]
    scored = [{"spec": r["spec"], "scores": score_world_v2(r), "run": r} for r in runs]
    keys = tuple(scored[0]["scores"])
    frontier = []
    for x in scored:
        if not any(all(y["scores"][k] >= x["scores"][k] for k in keys) and
                   any(y["scores"][k] > x["scores"][k] for k in keys) for y in scored if y is not x):
            frontier.append(x)
    frontier.sort(key=lambda x: (-x["scores"]["ensemble_reach"], -x["scores"]["long_arc"], x["spec"]["world_id"]))
    return {"version": 2, "count": count, "weeks": weeks, "master_seed": master_seed,
            "runs": scored, "pareto_frontier": frontier,
            "status": "scouting_noncanonical_requires_deep_replay"}
