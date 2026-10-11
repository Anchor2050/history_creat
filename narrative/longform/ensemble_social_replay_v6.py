"""Ensemble social-replay layer for the fourteen-person 2026-2035 branch.

This module does not replace StoryBox/Reverie. It decides when people plausibly
enter the same social window and packages the state that Reverie should replay.
The lower-level career/finance/household system remains the hard-constraint layer.
"""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import random

from . import career_six_2035 as base
from . import career_six_income_v5 as v5

ORIGINAL_ACTORS = (
    "lin_jing", "chen_lan", "xu_hang", "wu_cheng",
    "shen_yan", "gu_wei", "zhao_ke", "sun_jie",
)
ENSEMBLE_ACTORS = ORIGINAL_ACTORS + base.NEW_ACTORS

PERSONAL_SCENES = {
    "lin_jing": {
        "career": "doctoral research -> career and city choice",
        "private": "reciprocity, autonomy, and the cost of keeping options open",
        "social_hooks": ["roommate history", "public-sector comparison", "methods friends"],
    },
    "chen_lan": {
        "career": "doctoral completion -> external project work -> postdoctoral labor market",
        "private": "financial buffer, boundaries, and old relationships after refusal",
        "social_hooks": ["roommate history", "former group", "industry/project network"],
    },
    "xu_hang": {
        "career": "reproducibility work -> independent research identity",
        "private": "recognition, old attachment, and whether quiet technical work becomes valued",
        "social_hooks": ["former group", "verification peers", "cross-school doctoral friends"],
    },
    "wu_cheng": {
        "career": "supervisor and project owner under limited attention",
        "private": "how reliability expectations shift hidden work onto others",
        "social_hooks": ["students", "faculty peers", "project deadlines"],
    },
    "shen_yan": {
        "career": "supervisor building a research group with scarce mentoring time",
        "private": "the gap between being available and being easy to ask for help",
        "social_hooks": ["students", "methods seminar", "faculty network"],
    },
    "gu_wei": {
        "career": "supervisor prioritizing verifiable results and independent trainees",
        "private": "when to spend reputation on recommendations",
        "social_hooks": ["verification work", "student network", "faculty referrals"],
    },
    "zhao_ke": {
        "career": "project manager balancing delivery, budget, and reliable collaborators",
        "private": "trust under client pressure and repeated favors",
        "social_hooks": ["industry projects", "health-data work", "contract meals"],
    },
    "sun_jie": {
        "career": "graduate coordinator inside queues, rules, and bounded discretion",
        "private": "the emotional load of being treated as a doorway to an institution",
        "social_hooks": ["student affairs", "public-institution information", "campus alumni"],
    },
    "zhou_ye": {
        "career": "probability PhD with zero publications seeking a stable technical route",
        "private": "only-child care horizon and the meaning of professional dignity after rejection",
        "social_hooks": ["same-class trio", "verification peer", "stable-work comparison"],
    },
    "gao_yuan": {
        "career": "probability PhD preparing for public-sector recruitment",
        "private": "exam failure, hometown return option, and comparison with classmates",
        "social_hooks": ["same-class trio", "public-sector preparation", "alumni meals"],
    },
    "luo_cheng": {
        "career": "probability PhD translating doctoral identity into student-affairs work",
        "private": "age pressure and loss/reconstruction of academic identity",
        "social_hooks": ["same-class trio", "student-affairs information", "university peers"],
    },
    "tang_yu": {
        "career": "survival-analysis researcher aiming for a faculty position",
        "private": "research ambition inside sibling-care bargaining",
        "social_hooks": ["same-class trio", "methods seminar", "verification collaboration"],
    },
    "he_xin": {
        "career": "survival-analysis PhD comparing civil-service and public-institution routes",
        "private": "family boundary setting and the price of stability",
        "social_hooks": ["same-class trio", "public-sector information", "career comparison"],
    },
    "song_nan": {
        "career": "survival-analysis PhD translating methods into pharmaceutical work",
        "private": "industry identity, family bargaining, and whether she can later return to research",
        "social_hooks": ["same-class trio", "health-data project", "industry translation"],
    },
}

ORIGINAL_PROFILES = {
    "lin_jing": {"name": "林静", "age_2026": 28, "organization": "university_a", "field": "social_research"},
    "chen_lan": {"name": "陈岚", "age_2026": 31, "organization": "university_a", "field": "social_research"},
    "xu_hang": {"name": "许航", "age_2026": 27, "organization": "university_b", "field": "urban_computation"},
    "wu_cheng": {"name": "吴澄", "age_2026": 48, "organization": "university_a", "field": "supervision"},
    "shen_yan": {"name": "沈雁", "age_2026": 43, "organization": "university_a", "field": "methods"},
    "gu_wei": {"name": "顾维", "age_2026": 39, "organization": "university_b", "field": "verification"},
    "zhao_ke": {"name": "赵珂", "age_2026": 36, "organization": "mingheng", "field": "project_management"},
    "sun_jie": {"name": "孙洁", "age_2026": 35, "organization": "university_a", "field": "graduate_administration"},
}


def load_social_design(path=None):
    path = path or (
        Path(__file__).resolve().parents[2]
        / "docs" / "scenarios" / "career-six-social-graph-v1.json"
    )
    with open(path, encoding="utf-8") as handle:
        design = json.load(handle)
    if design.get("spec_version") != 1:
        raise ValueError("social design requires spec_version 1")
    if tuple(design.get("main_actors", ())) != ENSEMBLE_ACTORS:
        raise ValueError("social design actor order does not match ensemble")
    return design


def _pair(a, b):
    if a == b:
        raise ValueError("self ties are invalid")
    return tuple(sorted((a, b)))


def _new_actor_profiles(career_design):
    profiles = {}
    for actor_id, row in career_design["actors"].items():
        profiles[actor_id] = {
            "name": row["name"],
            "age_2026": row["age"],
            "organization": row["organization"],
            "field": row["field"],
        }
    return profiles


def _profiles(career_design):
    return {**deepcopy(ORIGINAL_PROFILES), **_new_actor_profiles(career_design)}


def _initial_ties(social_design):
    ties = {}
    for row in social_design["initial_ties"]:
        kind = row["kind"]
        kind_spec = social_design["tie_kinds"][kind]
        key = _pair(row["a"], row["b"])
        if key in ties:
            raise ValueError(f"duplicate tie {key}")
        ties[key] = {
            "a": key[0],
            "b": key[1],
            "kind": kind,
            "contexts": [row["context"]],
            "trust": float(row["trust"]),
            "closeness": float(kind_spec["base_closeness"]),
            "contact_days": int(kind_spec["contact_days"]),
            "introduction_power": float(kind_spec["introduction_power"]),
            "contact_count": 0,
            "last_contact": None,
            "origin": "initial_seed",
            "introduced_by": None,
            "shared_events": [],
        }
    return ties


def _year_snapshot(career_run, year):
    rows = career_run["annual_snapshots"]
    exact = next((row for row in rows if row["year"] == year), None)
    if exact:
        return exact
    earlier = [row for row in rows if row["year"] < year]
    return earlier[-1] if earlier else None


def _new_actor_context(career_run, actor_id, year):
    snapshot = _year_snapshot(career_run, year)
    if not snapshot:
        actor = career_run["actors"][actor_id]
        return {
            "stage": actor["stage"],
            "sector": actor["sector"],
            "city": actor["city_state"],
            "cash": career_run["ledger"]["accounts"][actor_id],
            "care_load": actor.get("family_care_load", 0.0),
            "housing": deepcopy(career_run["housing"].get(actor_id, {})),
        }
    actor = snapshot["actors"][actor_id]
    return {
        "stage": actor["stage"],
        "sector": actor["sector"],
        "city": actor["city_state"],
        "cash": snapshot["accounts"][actor_id],
        "care_load": actor.get("family_care_load", 0.0),
        "housing": deepcopy(snapshot["housing"].get(actor_id, {})),
    }


def _old_actor_context(actor_id, year, month, rng):
    scene = PERSONAL_SCENES[actor_id]
    base_pressure = {
        "lin_jing": .46, "chen_lan": .60, "xu_hang": .48, "wu_cheng": .68,
        "shen_yan": .61, "gu_wei": .57, "zhao_ke": .66, "sun_jie": .63,
    }[actor_id]
    seasonal = .07 if month in (3, 6, 10, 12) else 0.0
    drift = min(.12, .012 * max(0, year - 2026))
    pressure = max(.08, min(.96, base_pressure + seasonal + drift + rng.uniform(-.10, .10)))
    return {
        "stage": "professional_or_doctoral_continuation",
        "sector": ORIGINAL_PROFILES[actor_id]["organization"],
        "city": "beijing" if actor_id != "zhao_ke" else "beijing_market_network",
        "cash": None,
        "care_load": None,
        "housing": {},
        "scene_pressure": round(pressure, 4),
        "career_scene": scene["career"],
        "private_scene": scene["private"],
    }


def _hard_context(career_run, actor_id, year, month, rng):
    if actor_id in base.NEW_ACTORS:
        context = _new_actor_context(career_run, actor_id, year)
        context["scene_pressure"] = min(
            .95,
            .30
            + .30 * context["care_load"]
            + (.16 if context["stage"] == "search" else 0.0)
            + rng.uniform(0.0, .14),
        )
        context["career_scene"] = PERSONAL_SCENES[actor_id]["career"]
        context["private_scene"] = PERSONAL_SCENES[actor_id]["private"]
        return context
    return _old_actor_context(actor_id, year, month, rng)


def _attendance_probability(actor_id, event, context, rng):
    probability = float(event["attendance_base"])
    pressure = float(context.get("scene_pressure", .5))
    probability *= max(.35, 1.0 - .52 * pressure)

    if context.get("stage") == "search" and event["kind"] in {
        "recruitment_information_session", "alumni_methods_meetup",
        "cross_school_friend_dinner",
    }:
        probability += .14

    if event["kind"] in {"friend_trip", "weekend_outing"}:
        if context.get("care_load") and context["care_load"] > .25:
            probability -= .15
        if context.get("cash") is not None and context["cash"] < 7000:
            probability -= .18

    city = context.get("city")
    if event["mode"] == "in_person" and city not in {
        None, "beijing", "beijing_training", "beijing_market_network"
    }:
        probability -= .22

    if event["mode"] != "in_person":
        probability += .08

    return max(.04, min(.95, probability + rng.uniform(-.06, .06)))


def _months():
    year, month = 2026, 3
    while (year, month) <= (2035, 12):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def _month_index(year, month):
    return (year - 2026) * 12 + (month - 3)


def _recurring_due(ritual, year, month):
    if ritual.get("month") is not None:
        return month == ritual["month"]
    index = _month_index(year, month)
    return index >= 0 and index % int(ritual["cadence_months"]) == 0


def _event_mode(kind, rng):
    if kind in {"group_chat_revival"}:
        return "wechat_group"
    if kind in {"recruitment_information_session"} and rng.random() < .28:
        return "video_call"
    if kind in {"project_meal", "classmate_meal", "old_peer_meal", "friend_trip",
                "year_end_gathering", "weekend_outing", "conference_meal",
                "wedding_or_life_event", "cross_school_friend_dinner",
                "alumni_methods_meetup", "unexpected_city_overlap"}:
        return "in_person"
    return rng.choice(["in_person", "wechat_group", "phone"])


def _event_location(kind, mode, rng):
    if mode == "wechat_group":
        return "digital:wechat_group"
    if mode == "video_call":
        return "digital:video_call"
    if mode == "phone":
        return "digital:phone"
    if kind in {"friend_trip", "weekend_outing"}:
        return rng.choice(["beijing_outskirts", "nearby_city_trip", "mountain_or_lake_trip"])
    if kind == "conference_meal":
        return "conference_city_restaurant"
    if kind == "unexpected_city_overlap":
        return "temporary_shared_city"
    return rng.choice(["beijing_restaurant", "campus_cafe", "private_home", "city_park"])


def _tie(ties, a, b):
    return ties.get(_pair(a, b))


def _neighbors(ties, actor_id):
    rows = []
    for tie in ties.values():
        if actor_id == tie["a"]:
            rows.append((tie["b"], tie))
        elif actor_id == tie["b"]:
            rows.append((tie["a"], tie))
    return rows


def _shared_context_score(profiles, a, b):
    left, right = profiles[a], profiles[b]
    score = 0.0
    if left["organization"] == right["organization"]:
        score += .34
    if left["field"] == right["field"]:
        score += .28
    if "university" in left["organization"] and "university" in right["organization"]:
        score += .16
    if {a, b} <= set(base.NEW_ACTORS):
        score += .08
    return min(1.0, score)


def _select_connected_participants(anchor, pool, ties, limit, rng):
    scored = []
    for candidate in pool:
        if candidate == anchor:
            continue
        tie = _tie(ties, anchor, candidate)
        if tie:
            score = .60 * tie["trust"] + .40 * tie["closeness"] + rng.uniform(-.10, .10)
            scored.append((score, candidate))
    scored.sort(reverse=True)
    selected = [anchor] + [candidate for _, candidate in scored[: max(0, limit - 1)]]
    return selected


def _occasional_event(social_design, profiles, ties, year, month, rng):
    candidates = []
    for spec in social_design["occasional_event_types"]:
        if rng.random() < float(spec["annual_probability"]) / 12.0:
            candidates.append(spec)
    if not candidates:
        return None

    spec = rng.choice(candidates)
    degree = {
        actor_id: 1 + len(_neighbors(ties, actor_id))
        for actor_id in ENSEMBLE_ACTORS
    }
    anchors = list(degree)
    anchor = rng.choices(anchors, weights=[degree[x] for x in anchors], k=1)[0]
    size = rng.randint(int(spec["min_people"]), int(spec["max_people"]))
    participants = _select_connected_participants(
        anchor, ENSEMBLE_ACTORS, ties, size, rng
    )

    if len(participants) < size and spec["kind"] in {
        "conference_meal", "recruitment_information_session",
        "wedding_or_life_event", "group_chat_revival",
    }:
        remaining = [x for x in ENSEMBLE_ACTORS if x not in participants]
        rng.shuffle(remaining)
        participants.extend(remaining[: size - len(participants)])

    return {
        "id": f"occasional:{spec['kind']}:{year:04d}-{month:02d}:{rng.randrange(10**6):06d}",
        "kind": spec["kind"],
        "participants": participants,
        "attendance_base": .58,
        "mode": _event_mode(spec["kind"], rng),
        "location": None,
        "source": "occasional",
        "anchor": anchor,
    }


def _ritual_event(ritual, year, month, rng):
    kind = ritual["kind"]
    return {
        "id": f"ritual:{ritual['id']}:{year:04d}-{month:02d}",
        "kind": kind,
        "participants": list(ritual["participants"]),
        "attendance_base": float(ritual["attendance_base"]),
        "mode": _event_mode(kind, rng),
        "location": None,
        "source": "recurring_ritual",
        "anchor": ritual["participants"][0],
    }


def _attend(event, career_run, year, month, rng):
    contexts = {}
    attendees = []
    for actor_id in event["participants"]:
        context = _hard_context(career_run, actor_id, year, month, rng)
        contexts[actor_id] = context
        probability = _attendance_probability(actor_id, event, context, rng)
        if rng.random() < probability:
            attendees.append(actor_id)
    if event["anchor"] not in attendees:
        attendees.insert(0, event["anchor"])
    attendees = list(dict.fromkeys(attendees))
    return attendees, contexts


def _strengthen_tie(tie, event, when):
    intensity = {
        "friend_trip": .055,
        "weekend_outing": .045,
        "classmate_meal": .032,
        "old_peer_meal": .034,
        "year_end_gathering": .035,
        "cross_school_friend_dinner": .030,
        "alumni_methods_meetup": .025,
        "conference_meal": .021,
        "wedding_or_life_event": .030,
        "project_meal": .024,
        "group_chat_revival": .014,
        "recruitment_information_session": .012,
        "unexpected_city_overlap": .028,
    }.get(event["kind"], .018)
    tie["closeness"] = min(1.0, tie["closeness"] + intensity)
    tie["trust"] = min(1.0, tie["trust"] + .55 * intensity)
    tie["contact_count"] += 1
    tie["last_contact"] = when
    tie["shared_events"].append(event["id"])


def _possible_connector(ties, attendees, a, b):
    connectors = []
    for person in attendees:
        if person in (a, b):
            continue
        left, right = _tie(ties, person, a), _tie(ties, person, b)
        if left and right:
            strength = min(left["trust"], right["trust"])
            power = min(left["introduction_power"], right["introduction_power"])
            connectors.append((strength * power, person))
    if not connectors:
        return None
    connectors.sort(reverse=True)
    return connectors[0][1]


def _introduce_new_ties(social_design, profiles, ties, event, attendees, when, rng):
    rules = social_design["introduction_rules"]
    introduced = []
    pairs = []
    for i, a in enumerate(attendees):
        for b in attendees[i + 1:]:
            if _tie(ties, a, b):
                continue
            connector = _possible_connector(ties, attendees, a, b)
            open_context = event["kind"] in {
                "conference_meal", "recruitment_information_session",
                "wedding_or_life_event", "group_chat_revival",
            }
            if connector is None and not open_context:
                continue
            context_score = _shared_context_score(profiles, a, b)
            connector_bonus = .20 if connector else .06
            probability = .12 + .42 * context_score + connector_bonus
            if rng.random() < probability:
                pairs.append((a, b, connector, context_score))

    rng.shuffle(pairs)
    for a, b, connector, context_score in pairs[: int(rules["max_new_introductions_per_event"])]:
        trust = rng.uniform(*rules["new_tie_trust_range"])
        closeness = rng.uniform(*rules["new_tie_closeness_range"])
        key = _pair(a, b)
        ties[key] = {
            "a": key[0],
            "b": key[1],
            "kind": rules["new_tie_kind"],
            "contexts": [event["kind"]],
            "trust": trust,
            "closeness": closeness,
            "contact_days": int(social_design["tie_kinds"][rules["new_tie_kind"]]["contact_days"]),
            "introduction_power": float(
                social_design["tie_kinds"][rules["new_tie_kind"]]["introduction_power"]
            ),
            "contact_count": 1,
            "last_contact": when,
            "origin": "event_introduction",
            "introduced_by": connector,
            "shared_events": [event["id"]],
        }
        introduced.append({
            "a": a,
            "b": b,
            "introduced_by": connector,
            "context_score": round(context_score, 4),
        })
    return introduced


def _decay_ties(ties, year, month):
    if month != 12:
        return
    current = date(year, month, 1)
    for tie in ties.values():
        if not tie["last_contact"]:
            tie["closeness"] = max(.08, tie["closeness"] - .018)
            continue
        last = date.fromisoformat(tie["last_contact"])
        days = (current - last).days
        expected = max(14, tie["contact_days"])
        if days > 2 * expected:
            scale = min(3.0, days / (365.0 + expected))
            tie["closeness"] = max(.08, tie["closeness"] - .020 * scale)
            tie["trust"] = max(.12, tie["trust"] - .008 * scale)


def _persona_seed(actor_id, profile, context, year):
    scene = PERSONAL_SCENES[actor_id]
    age = int(profile["age_2026"] + (year - 2026))
    innate = {
        "lin_jing": "observant, academically proactive, private about disappointment",
        "chen_lan": "responsible, boundary-conscious, slow to disclose burden",
        "xu_hang": "reciprocal, technically careful, sensitive to unreturned attachment",
        "wu_cheng": "pragmatic, deadline-driven, relies on dependable people",
        "shen_yan": "method-oriented, supportive when requests are concrete",
        "gu_wei": "verification-oriented, careful with authority and recommendations",
        "zhao_ke": "delivery-focused, budget-aware, values reliable collaborators",
        "sun_jie": "procedural, calm, helpful within institutional boundaries",
        "zhou_ye": "technically serious, stability-seeking, self-conscious about zero publications",
        "gao_yuan": "disciplined, exam-oriented, comparison-sensitive",
        "luo_cheng": "people-oriented, reflective about status and identity",
        "tang_yu": "research-ambitious, analytical, protective of autonomy",
        "he_xin": "practical, stability-seeking, attentive to family boundaries",
        "song_nan": "translation-oriented, curious about industry, keeps a research identity",
    }[actor_id]
    currently = (
        f"{scene['career']}. Current hard context: stage={context.get('stage')}, "
        f"sector={context.get('sector')}, city={context.get('city')}. "
        f"Current private pressure: {scene['private']}."
    )
    lifestyle = (
        "Maintains different circles rather than one universal friend group; "
        "social contact depends on work pressure, city, money, care duties, and prior trust."
    )
    requirements = [
        "protect current work/family obligations before accepting optional social plans",
        "respond differently to close friends, classmates, alumni, work peers, and weak ties",
        "do not share private information unless it has actually been disclosed",
        "remember prior help, disappointment, introductions, and unresolved obligations",
    ]
    return {
        "name": profile["name"],
        "age": age,
        "innate": innate,
        "learned": f"Social hooks: {', '.join(scene['social_hooks'])}.",
        "currently": currently,
        "lifestyle": lifestyle,
        "living_area": f"Ensemble World:{context.get('city') or 'beijing'}:Everyday Life:Current Base",
        "att_bandwidth": 3,
        "retention": 8,
        "recency_w": 1,
        "relevance_w": 1,
        "importance_w": 1,
        "recency_decay": .992,
        "importance_trigger_max": 150,
        "importance_trigger_curr": 150,
        "importance_ele_n": 0,
        "thought_count": 5,
        "daily_plan_requirement": requirements,
    }


def _relationship_memory(actor_id, attendees, ties, profiles):
    rows = []
    for other in attendees:
        if other == actor_id:
            continue
        tie = _tie(ties, actor_id, other)
        if not tie:
            continue
        rows.append({
            "about": other,
            "name": profiles[other]["name"],
            "kind": tie["kind"],
            "trust": round(tie["trust"], 4),
            "closeness": round(tie["closeness"], 4),
            "last_contact": tie["last_contact"],
            "contexts": list(tie["contexts"]),
            "introduced_by": tie["introduced_by"],
        })
    return rows


def _micro_window_days(social_design, event):
    key = "ordinary_social_event"
    if event["kind"] in {"friend_trip", "weekend_outing"}:
        key = "trip_or_extended_gathering"
    elif event["kind"] in {"recruitment_information_session", "project_meal"}:
        key = "career_or_family_turning_point"
    return int(social_design["micro_replay_window_days"][key])


def _build_packet(
    social_design, profiles, ties, event, attendees, contexts,
    introductions, year, month, rng,
):
    start = date(year, month, rng.randint(3, 24))
    days = _micro_window_days(social_design, event)
    end = start + timedelta(days=days - 1)
    event["location"] = event["location"] or _event_location(
        event["kind"], event["mode"], rng
    )
    persona_seeds = {}
    memory_seeds = {}
    hard_constraints = {}
    for actor_id in attendees:
        hard_constraints[actor_id] = deepcopy(contexts[actor_id])
        persona_seeds[actor_id] = _persona_seed(
            actor_id, profiles[actor_id], contexts[actor_id], year
        )
        memory_seeds[actor_id] = {
            "relationships": _relationship_memory(actor_id, attendees, ties, profiles),
            "event_context": {
                "event_id": event["id"],
                "kind": event["kind"],
                "mode": event["mode"],
                "location": event["location"],
                "introduced_people": [
                    row for row in introductions if actor_id in (row["a"], row["b"])
                ],
            },
        }

    return {
        "packet_version": 1,
        "id": f"micro:{event['id']}",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "event_kind": event["kind"],
        "source": event["source"],
        "mode": event["mode"],
        "location": event["location"],
        "participants": list(attendees),
        "anchor": event["anchor"],
        "introductions": deepcopy(introductions),
        "hard_constraints": hard_constraints,
        "persona_seeds": persona_seeds,
        "memory_seeds": memory_seeds,
        "reverie_contract": {
            "workflow": ["perceive", "retrieve", "plan", "execute", "long_term_memory"],
            "use_existing_persona_cognition": True,
            "no_unearned_knowledge": True,
            "remote_chat_must_not_teleport": True,
            "in_person_requires_shared_venue": True,
            "output_required": [
                "events", "chat_memories", "relationship_updates",
                "commitments_or_refusals", "new_information_flows",
            ],
        },
        "status": "noncanonical_micro_replay_packet",
    }


def _apply_event(
    social_design, profiles, ties, event, career_run, year, month, rng,
):
    attendees, contexts = _attend(event, career_run, year, month, rng)
    if len(attendees) < 2:
        return None
    when = date(year, month, 1).isoformat()
    for i, a in enumerate(attendees):
        for b in attendees[i + 1:]:
            tie = _tie(ties, a, b)
            if tie:
                _strengthen_tie(tie, event, when)
    introductions = _introduce_new_ties(
        social_design, profiles, ties, event, attendees, when, rng
    )
    return _build_packet(
        social_design, profiles, ties, event, attendees, contexts,
        introductions, year, month, rng,
    )


def _career_trigger_packets(career_run, social_design, profiles, ties, rng):
    packets = []
    significant = []
    for row in career_run["job_cycles"] + career_run["reentries"]:
        if row.get("outcome") in {"accepted", "offer_rejected", "blocked"}:
            significant.append((row["date"], row["actor"], f"career_{row['outcome']}"))
    for row in career_run["home_purchases"]:
        significant.append((row["date"], row["actor"], "home_purchase"))
    for row in career_run["family_events"]:
        if row.get("care_load", 0) >= .22:
            significant.append((row["date"], row["actor"], "family_care_pressure"))

    for raw_date, actor_id, kind in significant:
        when = date.fromisoformat(raw_date)
        neighbors = sorted(
            _neighbors(ties, actor_id),
            key=lambda item: (.55 * item[1]["trust"] + .45 * item[1]["closeness"]),
            reverse=True,
        )
        participants = [actor_id] + [other for other, _ in neighbors[:3]]
        if len(participants) < 2:
            continue
        event = {
            "id": f"trigger:{kind}:{actor_id}:{raw_date}",
            "kind": kind,
            "participants": participants,
            "attendance_base": .70,
            "mode": rng.choice(["wechat_private", "phone", "in_person"]),
            "location": None,
            "source": "hard_world_trigger",
            "anchor": actor_id,
        }
        packet = _apply_event(
            social_design, profiles, ties, event, career_run,
            when.year, when.month, rng,
        )
        if packet:
            packet["reverie_contract"]["turning_point"] = kind
            packets.append(packet)
    return packets


def simulate_ensemble_social_replay(seed=1, career_run=None, social_design=None):
    """Build social history and StoryBox-ready replay windows for all 14 people.

    This function schedules contact and introductions; it does not fabricate
    dialogue. Dialogue and fine-grained behavior belong to the Reverie bridge.
    """
    career_run = deepcopy(career_run or v5.simulate_career_six_income(seed=seed))
    social_design = deepcopy(social_design or load_social_design())
    career_design = base.load_career_six_design()
    profiles = _profiles(career_design)
    ties = _initial_ties(social_design)
    rng = random.Random(seed + 600_000)

    packets = []
    for year, month in _months():
        for ritual in social_design["recurring_social_rituals"]:
            if not _recurring_due(ritual, year, month):
                continue
            event = _ritual_event(ritual, year, month, rng)
            packet = _apply_event(
                social_design, profiles, ties, event, career_run, year, month, rng
            )
            if packet:
                packets.append(packet)

        occasional = _occasional_event(
            social_design, profiles, ties, year, month, rng
        )
        if occasional:
            packet = _apply_event(
                social_design, profiles, ties, occasional,
                career_run, year, month, rng,
            )
            if packet:
                packets.append(packet)
        _decay_ties(ties, year, month)

    packets.extend(
        _career_trigger_packets(
            career_run, social_design, profiles, ties, rng
        )
    )
    packets.sort(key=lambda row: (row["start_date"], row["id"]))

    actor_event_counts = {actor_id: 0 for actor_id in ENSEMBLE_ACTORS}
    actor_introduction_counts = {actor_id: 0 for actor_id in ENSEMBLE_ACTORS}
    for packet in packets:
        for actor_id in packet["participants"]:
            actor_event_counts[actor_id] += 1
        for row in packet["introductions"]:
            actor_introduction_counts[row["a"]] += 1
            actor_introduction_counts[row["b"]] += 1

    return {
        "seed": seed,
        "status": "fourteen_person_ensemble_social_v6_noncanonical",
        "actors": deepcopy(profiles),
        "personal_scenes": deepcopy(PERSONAL_SCENES),
        "social_graph": {
            "ties": [deepcopy(tie) for tie in ties.values()],
            "actor_event_counts": actor_event_counts,
            "actor_introduction_counts": actor_introduction_counts,
        },
        "micro_replay_packets": packets,
        "career_world_status": career_run["status"],
        "social_design_principles": deepcopy(social_design["principles"]),
        "architecture": {
            "hard_world": "career_six_income_v5 and its household/city/finance layers",
            "social_scheduler": "ensemble_social_replay_v6",
            "micro_behavior": "Reverie Persona perceive/retrieve/plan/execute/memory",
            "story_generation": "Storyteller only after event replay",
        },
    }


def summarize_ensemble_structure(run):
    ties = run["social_graph"]["ties"]
    introduced = [row for row in ties if row["origin"] == "event_introduction"]
    strong = [
        row for row in ties
        if row["closeness"] >= .58 and row["trust"] >= .50
    ]
    return {
        "status": "structural_summary_noncanonical",
        "micro_windows": len(run["micro_replay_packets"]),
        "final_ties": len(ties),
        "introduced_ties": len(introduced),
        "strong_ties": len(strong),
        "actors_without_micro_scene": [
            actor_id
            for actor_id, count in run["social_graph"]["actor_event_counts"].items()
            if count == 0
        ],
        "actors_without_personal_scene": [
            actor_id for actor_id in ENSEMBLE_ACTORS
            if actor_id not in run["personal_scenes"]
        ],
    }
