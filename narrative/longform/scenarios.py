"""Compile long-form design documents into explicit executable initial state."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from .ledger import Ledger


class ScenarioError(ValueError):
    pass


def _date(value):
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except (TypeError, ValueError):
        raise ScenarioError(f"Invalid story date: {value!r}") from None


def _hours(actor):
    value = actor.get("weekly_discretionary_work_hours", actor.get("weekly_scenario_work_hours"))
    if type(value) is not int or value < 0:
        raise ScenarioError(f"Actor {actor.get('id')} lacks an integer weekly time budget")
    return value


def compile_beijing(design):
    """Return a versioned executable snapshot without mutating the design document.

    The design remains authoritative for identities and fictional starting facts.
    Compiler defaults below only make accounting and workflow state explicit.
    """
    if not isinstance(design, dict) or design.get("spec_version") != 1:
        raise ScenarioError("Expected Beijing design spec_version 1")
    actors = deepcopy(design.get("actors", {}))
    organizations = deepcopy(design.get("organizations", {}))
    if len(actors) != 8 or len(organizations) != 3:
        raise ScenarioError("Beijing v1 requires exactly 8 actors and 3 organizations")
    start = _date(design.get("start_date"))

    accounts = {}
    weekly_hours = {}
    for actor_id, actor in actors.items():
        if actor.get("id") != actor_id:
            raise ScenarioError(f"Actor ID mismatch: {actor_id}")
        weekly_hours[actor_id] = _hours(actor)
        if "cash" in actor:
            cash = actor["cash"]
            if type(cash) is not int or cash < 0:
                raise ScenarioError(f"Invalid cash for {actor_id}")
            accounts[actor_id] = cash

    # Institutional pools are named separately from people so transfers conserve money.
    for org_id, org in organizations.items():
        if "cash_available_for_project" in org:
            accounts[f"org:{org_id}:project"] = org["cash_available_for_project"]
        for budget_id, amount in org.get("earmarked_budgets", {}).items():
            accounts[f"org:{org_id}:budget:{budget_id}"] = amount

    # The design gives recurring stipends/support/expenses without source balances.
    # Explicit external source/sink accounts make future postings traceable while
    # preserving the supplied initial personal cash exactly.
    accounts["external:stipend_pool"] = 1_000_000
    accounts["external:family_pool"] = 1_000_000
    accounts["external:living_cost_sink"] = 0

    permissions = {}
    for org_id, org in organizations.items():
        for actor_id, grants in org.get("permissions", {}).items():
            permissions.setdefault(actor_id, set()).update(grants)

    ledger = Ledger(start, accounts, weekly_hours)
    old = design["contracts"]["old_delivery"]
    if old.get("status") == "accepted_unpaid":
        ledger.schedule_payment(
            "contract:old_delivery:payment",
            "org:mingheng:project",
            old["worker"],
            old["amount"],
            old["expected_payment_date"],
            "accepted old delivery",
        )

    artifacts = {}
    for artifact_id, artifact in design.get("artifacts", {}).items():
        artifacts[artifact_id] = {
            "id": artifact_id,
            **deepcopy(artifact),
            "version": 1,
            "review_status": "not_reviewed",
            "verification_status": "not_verified",
            "submission_status": "not_submitted",
            "history": [],
        }

    state = {
        "version": 1,
        "scenario": "beijing",
        "source_spec_version": design["spec_version"],
        "now": start,
        "actors": actors,
        "organizations": organizations,
        "relationships": deepcopy(design.get("relationships", [])),
        "contracts": deepcopy(design.get("contracts", {})),
        "artifacts": artifacts,
        "calendar": deepcopy(design.get("calendar", [])),
        "household": deepcopy(design.get("household", {})),
        "permissions": {k: sorted(v) for k, v in permissions.items()},
        "task_offers": {},
        "tasks": {},
        "reviews": {},
        "approvals": {},
        "events": [],
        "operation_receipts": {},
        "ledger": ledger.snapshot(),
        "compiler_notes": [
            "Institutional and external accounting pools are explicit runtime accounts.",
            "Old accepted delivery is scheduled for payment but may still block if funds are unavailable.",
            "Artifacts start with separate review, verification and submission states.",
            "Design-only implementation_gaps are retained in the source document; runtime code does not erase them.",
        ],
    }
    return state


def load_beijing(path=None):
    if path is None:
        path = Path(__file__).resolve().parents[2] / "docs" / "scenarios" / "beijing-doctoral-initial-v1.json"
    with open(path, "r", encoding="utf-8") as handle:
        return compile_beijing(json.load(handle))
