"""Persistent character plans, private knowledge, commitments and boundaries."""
from copy import deepcopy


class CharacterError(ValueError):
    pass


class Characters:
    def __init__(self, actors):
        self.state = {"version": 1, "characters": {}}
        for actor_id, actor in actors.items():
            self.state["characters"][actor_id] = {
                "id": actor_id,
                "goals": list(actor.get("goals", [])),
                "coping_style": actor.get("coping_style", ""),
                "known": set(actor.get("known_initial", [])),
                "private": set(actor.get("private_initial", [])),
                "plans": [],
                "commitments": [],
                "boundaries": [],
                "trust": {},
                "reflections": [],
                "experience_log": [],
            }

    def snapshot(self):
        result = deepcopy(self.state)
        for row in result["characters"].values():
            row["known"] = sorted(row["known"])
            row["private"] = sorted(row["private"])
        return result

    @classmethod
    def restore(cls, snapshot):
        if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
            raise CharacterError("Unsupported character snapshot")
        obj = cls.__new__(cls)
        obj.state = deepcopy(snapshot)
        for row in obj.state["characters"].values():
            row["known"] = set(row.get("known", []))
            row["private"] = set(row.get("private", []))
        return obj

    def _actor(self, actor):
        row = self.state["characters"].get(actor)
        if row is None:
            raise CharacterError("Unknown actor")
        return row

    def visible_context(self, actor, public_facts=None):
        row = self._actor(actor)
        return {
            "actor": actor,
            "goals": deepcopy(row["goals"]),
            "coping_style": row["coping_style"],
            "known": sorted(row["known"]),
            "private": sorted(row["private"]),
            "plans": deepcopy(row["plans"]),
            "commitments": deepcopy(row["commitments"]),
            "boundaries": deepcopy(row["boundaries"]),
            "trust": deepcopy(row["trust"]),
            "reflections": deepcopy(row["reflections"][-3:]),
            "public_facts": deepcopy(public_facts or {}),
        }

    def learn(self, actor, fact_id, private=False, source=None):
        if not isinstance(fact_id, str) or not fact_id:
            raise CharacterError("Fact ID required")
        row = self._actor(actor)
        target = row["private"] if private else row["known"]
        target.add(fact_id)
        row["experience_log"].append({"kind": "learn", "fact": fact_id, "private": private, "source": source})

    def add_plan(self, actor, plan_id, text, horizon_weeks, priority, evidence_ids):
        row = self._actor(actor)
        if type(horizon_weeks) is not int or horizon_weeks < 1 or type(priority) is not int:
            raise CharacterError("Plan needs positive horizon and integer priority")
        if not isinstance(text, str) or not text.strip() or not isinstance(evidence_ids, list):
            raise CharacterError("Plan needs text and evidence list")
        if any(p["id"] == plan_id for p in row["plans"]):
            raise CharacterError("Duplicate plan ID")
        row["plans"].append({"id": plan_id, "text": text, "horizon_weeks": horizon_weeks,
                             "priority": priority, "evidence_ids": list(evidence_ids), "status": "active"})
        row["plans"].sort(key=lambda p: (-p["priority"], p["id"]))

    def revise_plan(self, actor, plan_id, new_text, new_priority, evidence_ids, affected_commitments=None):
        row = self._actor(actor)
        plan = next((p for p in row["plans"] if p["id"] == plan_id), None)
        if plan is None:
            raise CharacterError("Unknown plan")
        if not evidence_ids or any(e not in row["known"] and e not in row["private"] for e in evidence_ids):
            raise CharacterError("Plan revision needs experiences this actor has actually seen")
        affected_commitments = affected_commitments or []
        known_commitments = {c["id"] for c in row["commitments"]}
        if any(c not in known_commitments for c in affected_commitments):
            raise CharacterError("Unknown affected commitment")
        before = deepcopy(plan)
        plan.update(text=new_text, priority=new_priority, evidence_ids=list(evidence_ids))
        row["experience_log"].append({"kind": "plan_revised", "plan": plan_id, "before": before,
                                      "after": deepcopy(plan), "evidence_ids": list(evidence_ids),
                                      "affected_commitments": list(affected_commitments)})
        row["plans"].sort(key=lambda p: (-p["priority"], p["id"]))

    def add_commitment(self, actor, commitment_id, text, to_actor=None, due=None):
        row = self._actor(actor)
        if any(c["id"] == commitment_id for c in row["commitments"]):
            raise CharacterError("Duplicate commitment")
        row["commitments"].append({"id": commitment_id, "text": text, "to_actor": to_actor,
                                   "due": due, "status": "active"})

    def set_boundary(self, actor, boundary_id, text, applies_to=None):
        row = self._actor(actor)
        existing = next((b for b in row["boundaries"] if b["id"] == boundary_id), None)
        value = {"id": boundary_id, "text": text, "applies_to": applies_to}
        if existing:
            existing.update(value)
        else:
            row["boundaries"].append(value)

    def reflect(self, actor, reflection_id, text, evidence_ids):
        row = self._actor(actor)
        if not evidence_ids or any(e not in row["known"] and e not in row["private"] for e in evidence_ids):
            raise CharacterError("Reflection needs actor-visible evidence")
        if any(r["id"] == reflection_id for r in row["reflections"]):
            raise CharacterError("Duplicate reflection")
        row["reflections"].append({"id": reflection_id, "text": text, "evidence_ids": list(evidence_ids)})

    def update_trust(self, actor, other, domain, delta, evidence_id):
        row = self._actor(actor)
        if evidence_id not in row["known"] and evidence_id not in row["private"]:
            raise CharacterError("Trust update needs actor-visible evidence")
        if type(delta) is not int or not -2 <= delta <= 2:
            raise CharacterError("Trust delta must be an integer from -2 to 2")
        key = f"{other}:{domain}"
        prior = row["trust"].get(key, 0)
        row["trust"][key] = max(-5, min(5, prior + delta))
        row["experience_log"].append({"kind": "trust_changed", "other": other, "domain": domain,
                                      "delta": delta, "evidence": evidence_id})
