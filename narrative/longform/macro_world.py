"""Slow-moving world layer for long-horizon narrative simulation.

The macro world does not choose for characters. It evolves public conditions
(technology, labor markets, housing, institutional finance, etc.) and projects
those conditions into actor-specific pressures. All values are fictional,
scenario-controlled indices rather than empirical forecasts.
"""
from copy import deepcopy
from datetime import date
from hashlib import sha256
import json


class MacroWorldError(ValueError):
    pass


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def _month(value):
    try:
        d = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise MacroWorldError(f"Invalid date: {value!r}") from None
    return d.replace(day=1).isoformat()


def _next_month(value):
    y, m, _ = map(int, value.split("-"))
    return f"{y + (m == 12):04d}-{1 if m == 12 else m + 1:02d}-01"


def beijing_2026_macro():
    """Return a deliberately small fictional macro scenario.

    Indices use 1.0 as the starting reference level. Trends are monthly changes.
    They are narrative assumptions, not claims about real Beijing or China.
    """
    return {
        "version": 1,
        "scenario": "beijing_long_horizon_fiction",
        "now": "2026-03-01",
        "signals": {
            "academic_job_availability": {
                "value": 1.00, "trend": -0.004, "min": 0.55, "max": 1.20,
                "meaning": "relative availability of early-career academic jobs",
            },
            "ai_research_capability": {
                "value": 1.00, "trend": 0.018, "min": 0.80, "max": 3.00,
                "meaning": "relative capability of AI research tooling",
            },
            "urban_housing_cost": {
                "value": 1.00, "trend": 0.0015, "min": 0.75, "max": 1.60,
                "meaning": "relative housing burden faced by young adults",
            },
            "university_discretionary_budget": {
                "value": 1.00, "trend": -0.0015, "min": 0.70, "max": 1.30,
                "meaning": "relative discretionary university research budget",
            },
            "research_outsourcing_demand": {
                "value": 1.00, "trend": 0.002, "min": 0.70, "max": 1.50,
                "meaning": "relative demand for external research-service work",
            },
        },
        "scheduled_changes": [
            {
                "id": "ai-tool-jump-2028",
                "month": "2028-09-01",
                "signal": "ai_research_capability",
                "delta": 0.20,
                "public_fact": "A new generation of research automation tools becomes widely usable.",
                "provenance": "fictional_scenario_assumption",
            },
            {
                "id": "university-budget-tightening-2029",
                "month": "2029-01-01",
                "signal": "university_discretionary_budget",
                "delta": -0.08,
                "public_fact": "Several universities tighten discretionary project spending.",
                "provenance": "fictional_scenario_assumption",
            },
        ],
        "events": [],
        "applied_changes": [],
    }


class MacroWorld:
    def __init__(self, state):
        self.state = deepcopy(state)
        self._validate()

    @classmethod
    def restore(cls, state):
        return cls(state)

    def snapshot(self):
        return deepcopy(self.state)

    def state_hash(self):
        return _digest(self.state)

    def _validate(self):
        if self.state.get("version") != 1:
            raise MacroWorldError("Unsupported macro world snapshot")
        self.state["now"] = _month(self.state.get("now"))
        signals = self.state.get("signals")
        if not isinstance(signals, dict) or not signals:
            raise MacroWorldError("Macro world requires signals")
        for name, row in signals.items():
            if not isinstance(name, str) or not isinstance(row, dict):
                raise MacroWorldError("Malformed signal")
            for key in ("value", "trend", "min", "max", "meaning"):
                if key not in row:
                    raise MacroWorldError(f"Signal {name} missing {key}")
            if not all(isinstance(row[k], (int, float)) for k in ("value", "trend", "min", "max")):
                raise MacroWorldError("Signal values must be numeric")
            if row["min"] > row["value"] or row["value"] > row["max"]:
                raise MacroWorldError(f"Signal {name} out of bounds")
        seen = set()
        for change in self.state.get("scheduled_changes", []):
            if change.get("id") in seen:
                raise MacroWorldError("Duplicate scheduled change")
            seen.add(change.get("id"))
            if change.get("signal") not in signals:
                raise MacroWorldError("Scheduled change targets unknown signal")
            _month(change.get("month"))
        if not isinstance(self.state.get("events"), list) or not isinstance(self.state.get("applied_changes"), list):
            raise MacroWorldError("Macro world requires event logs")

    def _record(self, kind, **fields):
        row = {"id": len(self.state["events"]) + 1, "kind": kind,
               "month": self.state["now"], **deepcopy(fields)}
        self.state["events"].append(row)
        return deepcopy(row)

    def _apply_month(self, month):
        self.state["now"] = month
        deltas = {}
        for name, row in self.state["signals"].items():
            before = row["value"]
            row["value"] = min(row["max"], max(row["min"], before + row["trend"]))
            deltas[name] = row["value"] - before

        applied_ids = set(self.state["applied_changes"])
        shocks = []
        for change in self.state.get("scheduled_changes", []):
            if change["id"] in applied_ids or _month(change["month"]) != month:
                continue
            row = self.state["signals"][change["signal"]]
            before = row["value"]
            row["value"] = min(row["max"], max(row["min"], before + change["delta"]))
            actual = row["value"] - before
            deltas[change["signal"]] += actual
            self.state["applied_changes"].append(change["id"])
            shocks.append({
                "change_id": change["id"],
                "signal": change["signal"],
                "delta": actual,
                "public_fact": change.get("public_fact", ""),
                "provenance": change.get("provenance", "scenario"),
            })
        self._record("macro_month", deltas=deltas, shocks=shocks,
                     signals={k: v["value"] for k, v in self.state["signals"].items()})

    def advance(self, target):
        target_month = _month(target)
        if target_month < self.state["now"]:
            raise MacroWorldError("Cannot move macro world backward")
        cursor = self.state["now"]
        while cursor < target_month:
            cursor = _next_month(cursor)
            self._apply_month(cursor)
        self._validate()
        return self.snapshot()

    def public_context(self):
        return {
            "month": self.state["now"],
            "signals": {
                name: {"value": row["value"], "meaning": row["meaning"]}
                for name, row in self.state["signals"].items()
            },
            "recent_events": deepcopy(self.state["events"][-6:]),
        }

    def pressures_for(self, exposure):
        """Project public conditions into one actor without choosing an action.

        exposure maps signal names to non-negative sensitivity weights. Returned
        pressure is signed relative to the reference value 1.0.
        """
        if not isinstance(exposure, dict):
            raise MacroWorldError("Exposure must be an object")
        items = []
        total = 0.0
        for signal, weight in exposure.items():
            if signal not in self.state["signals"]:
                raise MacroWorldError(f"Unknown exposure signal: {signal}")
            if not isinstance(weight, (int, float)) or weight < 0:
                raise MacroWorldError("Exposure weights must be non-negative")
            value = self.state["signals"][signal]["value"]
            signed = (value - 1.0) * float(weight)
            items.append({
                "signal": signal,
                "value": value,
                "weight": float(weight),
                "signed_pressure": signed,
            })
            total += signed
        return {
            "month": self.state["now"],
            "net_pressure": total,
            "components": items,
        }
