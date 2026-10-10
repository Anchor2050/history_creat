"""Social execution layer connecting topology, household obligations and frozen views."""
from copy import deepcopy

from .consequence_topology import ConsequenceTopology, TopologyError


class SocialEngineError(ValueError):
    pass


DEFAULT_HOUSEHOLDS = {
    "lin_jing": {
        "monthly_support": 1200,
        "monthly_obligation": 0,
        "care_hours_per_week": 1,
        "housing_need": 0.25,
    },
    "chen_lan": {
        "monthly_support": 0,
        "monthly_obligation": 1000,
        "care_hours_per_week": 3,
        "housing_need": 0.85,
    },
    "xu_hang": {
        "monthly_support": 0,
        "monthly_obligation": 0,
        "care_hours_per_week": 1,
        "housing_need": 0.35,
    },
}


class SocialEngine:
    """Bounded social authority above World and below character choice.

    It converts explicit household/resource consequences into feasible options.
    It never invents a character choice.
    """

    def __init__(self, topology=None, households=None):
        self.topology = topology or ConsequenceTopology()
        self.households = deepcopy(households or DEFAULT_HOUSEHOLDS)
        self.history = []
        self.frozen_views = {}

    def snapshot(self):
        return {
            "version": 1,
            "topology": self.topology.snapshot(),
            "households": deepcopy(self.households),
            "history": deepcopy(self.history),
            "frozen_views": deepcopy(self.frozen_views),
        }

    @classmethod
    def restore(cls, snapshot):
        if snapshot.get("version") != 1:
            raise SocialEngineError("Unsupported social-engine snapshot")
        obj = cls(
            ConsequenceTopology(snapshot["topology"]),
            snapshot["households"],
        )
        obj.history = deepcopy(snapshot.get("history", []))
        obj.frozen_views = deepcopy(snapshot.get("frozen_views", {}))
        return obj

    def _record(self, date, kind, actor=None, payload=None, cause_ids=None):
        row = {
            "id": f"social-{len(self.history)+1:05d}",
            "date": date,
            "kind": kind,
            "actor": actor,
            "payload": deepcopy(payload or {}),
            "cause_ids": list(cause_ids or []),
        }
        self.history.append(row)
        return deepcopy(row)

    def household_week(self, actor_id, date, cash, discretionary_hours, shock=None):
        """Apply material family consequences without mind control."""
        row = self.households.get(actor_id)
        if row is None:
            return {
                "cash_after": cash,
                "hours_after": discretionary_hours,
                "care_hours": 0,
                "events": [],
            }
        events = []
        care = int(row["care_hours_per_week"])
        if shock:
            delta_hours = int(shock.get("extra_care_hours", 0))
            delta_cash = int(shock.get("extra_obligation", 0))
            if delta_hours < 0 or delta_cash < 0:
                raise SocialEngineError("Household shocks cannot create negative obligations")
            care += delta_hours
            row["monthly_obligation"] += delta_cash
            events.append(self._record(
                date, "household_obligation_changed", actor_id,
                {"extra_care_hours": delta_hours, "extra_obligation": delta_cash},
            ))
        cash_flow = (row["monthly_support"] - row["monthly_obligation"]) / 4.345
        cash_after = cash + cash_flow
        hours_after = max(0, discretionary_hours - care)
        return {
            "cash_after": cash_after,
            "hours_after": hours_after,
            "care_hours": care,
            "events": events,
        }

    def set_household_obligation(self, actor_id, date, monthly_obligation=None,
                                 care_hours_per_week=None, cause_ids=None):
        row = self.households.get(actor_id)
        if row is None:
            raise SocialEngineError("Unknown household actor")
        before = deepcopy(row)
        if monthly_obligation is not None:
            if monthly_obligation < 0:
                raise SocialEngineError("Negative household obligation")
            row["monthly_obligation"] = int(monthly_obligation)
        if care_hours_per_week is not None:
            if care_hours_per_week < 0:
                raise SocialEngineError("Negative care hours")
            row["care_hours_per_week"] = int(care_hours_per_week)
        return self._record(
            date, "household_state_changed", actor_id,
            {"before": before, "after": deepcopy(row)}, cause_ids,
        )

    def material_options(self, actor_id, cash, weekly_hours):
        opts = self.topology.feasible_options(actor_id)
        family = self.households.get(actor_id, {})
        if cash < 8000 and weekly_hours >= 8 and actor_id == "chen_lan":
            if "seek_paid_research_work" not in opts and self.topology.resource_available(
                    "mingheng.paid_research_hours") >= 8:
                opts.append("seek_paid_research_work")
        if family.get("housing_need", 0) < 0.5 and "seek_transition_housing" in opts:
            opts.remove("seek_transition_housing")
        if weekly_hours < 3:
            opts = [x for x in opts if x not in {
                "request_advisor_attention", "seek_paid_research_work"
            }]
        return sorted(opts)

    def freeze_views(self, period_id, actor_states):
        """Freeze all views before any same-period action is committed."""
        if period_id in self.frozen_views:
            return deepcopy(self.frozen_views[period_id])
        views = {}
        for actor_id, state in actor_states.items():
            views[actor_id] = {
                "period": period_id,
                "actor": actor_id,
                "cash": state["cash"],
                "weekly_hours": state["weekly_hours"],
                "options": self.material_options(
                    actor_id, state["cash"], state["weekly_hours"]
                ),
                "household": deepcopy(self.households.get(actor_id)),
            }
        self.frozen_views[period_id] = views
        return deepcopy(views)

    def allocate_option(self, actor_id, option, date, cause_ids=None):
        mapping = {
            "request_advisor_attention": (
                f"{self.topology.state['actor_status'][actor_id]['institution']}.advisor_attention", 1
            ),
            "seek_recommendation": ("university_a.recommendation_slots", 1),
            "seek_bridge_funding": ("university_a.bridge_funding", 1000),
            "seek_transition_housing": ("university_a.transition_housing", 1),
            "seek_paid_research_work": ("mingheng.paid_research_hours", 8),
        }
        if option not in mapping:
            raise SocialEngineError("Unsupported option")
        resource, amount = mapping[option]
        node = self.topology.allocate(resource, actor_id, amount, date, cause_ids)
        self._record(
            date, "option_materialized", actor_id,
            {"option": option, "resource": resource, "amount": amount},
            [node["id"]],
        )
        return node

    def communicate(self, speaker, listener, fact_id, date, public=False, cause_ids=None):
        """Restricted information edge; downstream reputation needs this evidence."""
        if speaker == listener:
            raise SocialEngineError("Communication needs two actors")
        node = self.topology._node(
            "public_fact_transmitted" if public else "fact_transmitted",
            date, actor=speaker, target=listener,
            payload={"fact_id": fact_id, "public": bool(public)},
            causes=cause_ids,
        )
        self._record(
            date, "communication", speaker,
            {"listener": listener, "fact_id": fact_id, "public": bool(public)},
            [node["id"]],
        )
        return node

    def reputation_from_message(self, observer, actor, domain, delta, message_node, date):
        if message_node.get("kind") not in {"fact_transmitted", "public_fact_transmitted"}:
            raise SocialEngineError("Reputation update requires transmitted evidence")
        if message_node.get("target") != observer and message_node["kind"] != "public_fact_transmitted":
            raise SocialEngineError("Observer did not receive this evidence")
        return self.topology.update_reputation(
            observer, actor, domain, delta, date, [message_node["id"]]
        )
