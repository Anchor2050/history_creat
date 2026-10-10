"""Endogenous consequence topology for long-horizon social simulation.

This layer makes one actor's choices change other actors' feasible futures.
It owns shared scarce resources and an auditable causal graph. It does not
write prose, infer motives, or bypass the existing micro-world authority.
"""
from copy import deepcopy


class TopologyError(ValueError):
    pass


DEFAULT_TOPOLOGY = {
    "version": 1,
    "now": "2026-03-02",
    "resources": {
        "university_a.advisor_attention": {"capacity": 4.0, "allocations": {}},
        "university_a.recommendation_slots": {"capacity": 2.0, "allocations": {}},
        "university_a.bridge_funding": {"capacity": 6000.0, "allocations": {}},
        "university_a.transition_housing": {"capacity": 1.0, "allocations": {}},
        "university_b.advisor_attention": {"capacity": 3.0, "allocations": {}},
        "mingheng.paid_research_hours": {"capacity": 48.0, "allocations": {}},
    },
    "nodes": [],
    "edges": [],
    "actor_status": {
        "lin_jing": {"active": True, "institution": "university_a"},
        "chen_lan": {"active": True, "institution": "university_a"},
        "xu_hang": {"active": True, "institution": "university_b"},
        "wu_cheng": {"active": True, "institution": "university_a"},
        "shen_yan": {"active": True, "institution": "university_a"},
        "gu_wei": {"active": True, "institution": "university_b"},
        "zhao_ke": {"active": True, "institution": "mingheng"},
        "sun_jie": {"active": True, "institution": "university_a"},
    },
    "institution_memory": {},
    "reputation": {},
}


class ConsequenceTopology:
    def __init__(self, state=None):
        self.state = deepcopy(state or DEFAULT_TOPOLOGY)
        self._validate()

    def _validate(self):
        if self.state.get("version") != 1:
            raise TopologyError("Unsupported topology version")
        for key in ("resources", "nodes", "edges", "actor_status",
                    "institution_memory", "reputation"):
            if key not in self.state:
                raise TopologyError(f"Missing {key}")
        ids = [n["id"] for n in self.state["nodes"]]
        if len(ids) != len(set(ids)):
            raise TopologyError("Duplicate causal node id")

    def snapshot(self):
        return deepcopy(self.state)

    def _node(self, kind, date, actor=None, target=None, payload=None, causes=None):
        causes = list(causes or [])
        known = {n["id"] for n in self.state["nodes"]}
        if any(c not in known for c in causes):
            raise TopologyError("Unknown or future cause")
        node = {
            "id": f"cause-{len(self.state['nodes']) + 1:05d}",
            "date": date,
            "kind": kind,
            "actor": actor,
            "target": target,
            "payload": deepcopy(payload or {}),
            "causes": causes,
        }
        self.state["nodes"].append(node)
        for cause in causes:
            self.state["edges"].append({"from": cause, "to": node["id"]})
        self.state["now"] = max(self.state["now"], date)
        return deepcopy(node)

    def resource_available(self, resource_id):
        row = self.state["resources"].get(resource_id)
        if row is None:
            raise TopologyError("Unknown resource")
        return row["capacity"] - sum(row["allocations"].values())

    def allocate(self, resource_id, actor_id, amount, date, causes=None):
        if actor_id not in self.state["actor_status"] or not self.state["actor_status"][actor_id]["active"]:
            raise TopologyError("Inactive or unknown actor")
        if amount <= 0:
            raise TopologyError("Allocation must be positive")
        row = self.state["resources"].get(resource_id)
        if row is None:
            raise TopologyError("Unknown resource")
        if self.resource_available(resource_id) + 1e-12 < amount:
            raise TopologyError("Insufficient shared capacity")
        before = row["allocations"].get(actor_id, 0.0)
        row["allocations"][actor_id] = before + amount
        return self._node(
            "shared_resource_allocated", date, actor=actor_id, target=resource_id,
            payload={"amount": amount, "remaining": self.resource_available(resource_id)},
            causes=causes,
        )

    def release(self, resource_id, actor_id, amount, date, causes=None):
        row = self.state["resources"].get(resource_id)
        if row is None:
            raise TopologyError("Unknown resource")
        held = row["allocations"].get(actor_id, 0.0)
        if amount <= 0 or amount > held + 1e-12:
            raise TopologyError("Invalid release")
        left = held - amount
        if left <= 1e-12:
            row["allocations"].pop(actor_id, None)
        else:
            row["allocations"][actor_id] = left
        return self._node(
            "shared_resource_released", date, actor=actor_id, target=resource_id,
            payload={"amount": amount, "remaining": self.resource_available(resource_id)},
            causes=causes,
        )

    def remember(self, institution_id, key, value, date, causes=None):
        memory = self.state["institution_memory"].setdefault(institution_id, {})
        memory[key] = deepcopy(value)
        return self._node(
            "institution_memory_updated", date, target=f"{institution_id}.{key}",
            payload={"value": deepcopy(value)}, causes=causes,
        )

    def update_reputation(self, observer_id, actor_id, domain, delta, date, causes=None):
        if delta < -1.0 or delta > 1.0:
            raise TopologyError("Reputation delta out of bounds")
        key = f"{observer_id}|{actor_id}|{domain}"
        before = float(self.state["reputation"].get(key, 0.0))
        after = max(-1.0, min(1.0, before + delta))
        self.state["reputation"][key] = after
        return self._node(
            "reputation_updated", date, actor=observer_id, target=actor_id,
            payload={"domain": domain, "before": before, "after": after},
            causes=causes,
        )

    def exit_actor(self, actor_id, date, reason, causes=None):
        if actor_id not in self.state["actor_status"]:
            raise TopologyError("Unknown actor")
        self.state["actor_status"][actor_id]["active"] = False
        self.state["actor_status"][actor_id]["exit_reason"] = reason
        self.state["actor_status"][actor_id]["exit_date"] = date
        return self._node(
            "actor_exited", date, actor=actor_id,
            payload={"reason": reason}, causes=causes,
        )

    def feasible_options(self, actor_id):
        """Material options only; this function never chooses for the actor."""
        if actor_id not in self.state["actor_status"]:
            raise TopologyError("Unknown actor")
        if not self.state["actor_status"][actor_id]["active"]:
            return []
        opts = []
        inst = self.state["actor_status"][actor_id]["institution"]
        if inst == "university_a":
            if self.resource_available("university_a.advisor_attention") >= 1:
                opts.append("request_advisor_attention")
            if self.resource_available("university_a.recommendation_slots") >= 1:
                opts.append("seek_recommendation")
            if self.resource_available("university_a.bridge_funding") >= 1000:
                opts.append("seek_bridge_funding")
            if self.resource_available("university_a.transition_housing") >= 1:
                opts.append("seek_transition_housing")
        if actor_id == "chen_lan" and self.resource_available("mingheng.paid_research_hours") >= 8:
            opts.append("seek_paid_research_work")
        return opts

    def causal_trace(self, node_id):
        by_id = {n["id"]: n for n in self.state["nodes"]}
        if node_id not in by_id:
            raise TopologyError("Unknown node")
        seen = set()
        out = []

        def visit(nid):
            if nid in seen:
                return
            seen.add(nid)
            node = by_id[nid]
            for cause in node["causes"]:
                visit(cause)
            out.append(deepcopy(node))

        visit(node_id)
        return out
