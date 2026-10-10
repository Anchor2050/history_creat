"""Mesoscopic institutions between macro conditions and character choices.

The social world converts slow public signals into capacity constraints and notices.
It cannot choose for characters or mutate the micro ledger, consent, or permissions.
"""
from copy import deepcopy


class SocialWorldError(ValueError):
    pass


DEFAULT_STATE = {
    "version": 1,
    "institutions": {
        "university_a": {"research_capacity": 1.0, "junior_opportunity_capacity": 1.0, "admin_capacity": 1.0},
        "university_b": {"research_capacity": 1.0, "junior_opportunity_capacity": 1.0, "admin_capacity": 1.0},
        "mingheng": {"project_capacity": 1.0, "automation_substitution": 0.0},
    },
    "city": {"young_adult_housing_burden": 1.0},
    "families": {
        "lin_jing": {"cash_support_capacity": 1.0, "care_demand": 0.20},
        "chen_lan": {"cash_support_capacity": 0.55, "care_demand": 0.55},
        "xu_hang": {"cash_support_capacity": 0.80, "care_demand": 0.25},
    },
    "events": [],
}


class SocialWorld:
    def __init__(self, state=None):
        self.state = deepcopy(state or DEFAULT_STATE)
        self._validate()

    def _validate(self):
        if self.state.get("version") != 1:
            raise SocialWorldError("Unsupported social world")
        if not all(k in self.state for k in ("institutions", "city", "families", "events")):
            raise SocialWorldError("Incomplete social world")

    def snapshot(self):
        return deepcopy(self.state)

    def _record(self, month, kind, target, before, after, causes):
        if abs(after - before) < 1e-12:
            return
        self.state["events"].append({
            "id": len(self.state["events"]) + 1,
            "month": month,
            "kind": kind,
            "target": target,
            "before": before,
            "after": after,
            "causes": deepcopy(causes),
        })

    def update_from_macro(self, macro):
        """Deterministically propagate macro state through institutions/city.

        Each derived value stores its causal source in an event. The formulas are
        fictional scenario mechanics, intentionally simple enough to audit.
        """
        ctx = macro.public_context()
        month = ctx["month"]
        s = {k: v["value"] for k, v in ctx["signals"].items()}

        budget = s["university_discretionary_budget"]
        jobs = s["academic_job_availability"]
        ai = s["ai_research_capability"]
        outsourcing = s["research_outsourcing_demand"]
        housing = s["urban_housing_cost"]

        for uid in ("university_a", "university_b"):
            inst = self.state["institutions"][uid]
            derived = {
                "research_capacity": max(0.55, min(1.25, budget)),
                "junior_opportunity_capacity": max(0.45, min(1.20, 0.65 * jobs + 0.35 * budget)),
                "admin_capacity": max(0.70, min(1.15, 0.80 + 0.20 * budget)),
            }
            for key, value in derived.items():
                before = inst[key]; inst[key] = value
                self._record(month, "institution_capacity_changed", f"{uid}.{key}", before, value,
                             ["university_discretionary_budget", "academic_job_availability"])

        company = self.state["institutions"]["mingheng"]
        project_capacity = max(0.60, min(1.50, outsourcing * (1.0 + 0.08 * max(0.0, ai - 1.0))))
        automation = max(0.0, min(0.80, (ai - 1.0) * 0.35))
        for key, value, causes in (
            ("project_capacity", project_capacity, ["research_outsourcing_demand", "ai_research_capability"]),
            ("automation_substitution", automation, ["ai_research_capability"]),
        ):
            before = company[key]; company[key] = value
            self._record(month, "institution_capacity_changed", f"mingheng.{key}", before, value, causes)

        before = self.state["city"]["young_adult_housing_burden"]
        self.state["city"]["young_adult_housing_burden"] = housing
        self._record(month, "city_condition_changed", "city.young_adult_housing_burden", before, housing,
                     ["urban_housing_cost"])
        return self.snapshot()

    def actor_context(self, actor_id):
        """Return material constraints relevant to an actor, without a decision."""
        out = {"institutions": {}, "city": deepcopy(self.state["city"]), "family": None}
        if actor_id in {"lin_jing", "chen_lan", "wu_cheng", "shen_yan", "sun_jie"}:
            out["institutions"]["university_a"] = deepcopy(self.state["institutions"]["university_a"])
        if actor_id in {"xu_hang", "gu_wei"}:
            out["institutions"]["university_b"] = deepcopy(self.state["institutions"]["university_b"])
        if actor_id == "zhao_ke" or actor_id == "chen_lan":
            out["institutions"]["mingheng"] = deepcopy(self.state["institutions"]["mingheng"])
        if actor_id in self.state["families"]:
            out["family"] = deepcopy(self.state["families"][actor_id])
        return out
