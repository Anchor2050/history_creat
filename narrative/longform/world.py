"""Rule-enforced long-form world transitions for the Beijing scenario."""
from copy import deepcopy
from hashlib import sha256
import json

from .ledger import Ledger, LedgerError


class WorldError(ValueError):
    pass


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class World:
    def __init__(self, state):
        self.state = deepcopy(state)
        self._validate()

    @classmethod
    def restore(cls, state):
        return cls(state)

    def snapshot(self):
        return deepcopy(self.state)

    def state_hash(self):
        return _hash(self.state)

    def _validate(self):
        if self.state.get("version") != 1 or self.state.get("scenario") != "beijing":
            raise WorldError("Unsupported world snapshot")
        Ledger.restore(self.state["ledger"])
        actors = self.state["actors"]
        if set(self.state["permissions"]) - set(actors):
            raise WorldError("Unknown permission holder")
        for artifact_id, artifact in self.state["artifacts"].items():
            if artifact.get("id") != artifact_id or artifact.get("owner") not in actors:
                raise WorldError("Invalid artifact")
        for task_id, task in self.state["tasks"].items():
            if task.get("id") != task_id or task.get("assignee") not in actors:
                raise WorldError("Invalid task")

    def _record(self, kind, **fields):
        row = {"id": len(self.state["events"]) + 1, "kind": kind, "at": self.state["ledger"]["now"], **fields}
        self.state["events"].append(row)
        return deepcopy(row)

    def _op(self, operation_id, payload, fn):
        if not isinstance(operation_id, str) or not operation_id:
            raise WorldError("Operation ID required")
        receipt = self.state["operation_receipts"].get(operation_id)
        if receipt:
            if receipt["payload"] != payload:
                raise WorldError("Operation ID reused with different contents")
            return deepcopy(receipt["result"])
        before = self.snapshot()
        try:
            result = fn()
            self._validate()
        except Exception:
            self.state = before
            raise
        self.state["operation_receipts"][operation_id] = {"payload": deepcopy(payload), "result": deepcopy(result)}
        return deepcopy(result)

    def has_permission(self, actor, permission):
        return permission in self.state["permissions"].get(actor, [])

    def offer_task(self, operation_id, proposer, assignee, title, hours, permission=None, paid_amount=None):
        payload = dict(kind="offer_task", proposer=proposer, assignee=assignee, title=title, hours=hours,
                       permission=permission, paid_amount=paid_amount)
        def apply():
            if proposer not in self.state["actors"] or assignee not in self.state["actors"]:
                raise WorldError("Unknown actor")
            if not isinstance(title, str) or not title.strip() or type(hours) is not int or hours <= 0:
                raise WorldError("Task offer needs title and positive integer hours")
            if permission and not self.has_permission(proposer, permission):
                raise WorldError("Proposer lacks required permission")
            if paid_amount is not None and (type(paid_amount) is not int or paid_amount <= 0):
                raise WorldError("Paid amount must be a positive integer")
            offer = {"id": operation_id, "proposer": proposer, "assignee": assignee, "title": title,
                     "hours": hours, "paid_amount": paid_amount, "status": "offered", "accepted_by": None}
            self.state["task_offers"][operation_id] = offer
            self._record("task_offered", offer=operation_id, proposer=proposer, assignee=assignee)
            return offer
        return self._op(operation_id, payload, apply)

    def respond_task(self, operation_id, offer_id, actor, accept):
        payload = dict(kind="respond_task", offer=offer_id, actor=actor, accept=accept)
        def apply():
            offer = self.state["task_offers"].get(offer_id)
            if not offer or offer["status"] != "offered" or offer["assignee"] != actor:
                raise WorldError("No open task offer for this actor")
            if type(accept) is not bool:
                raise WorldError("Task response must be boolean")
            offer["status"] = "accepted" if accept else "declined"
            offer["accepted_by"] = actor if accept else None
            if accept:
                self.state["tasks"][offer_id] = {"id": offer_id, "assignee": actor, "proposer": offer["proposer"],
                    "title": offer["title"], "hours": offer["hours"], "paid_amount": offer["paid_amount"],
                    "status": "accepted", "artifact": None, "review": None, "verification": None, "submission": None}
            self._record("task_response", offer=offer_id, actor=actor, accepted=accept)
            return deepcopy(offer)
        return self._op(operation_id, payload, apply)

    def attach_artifact(self, operation_id, task_id, actor, artifact_id):
        payload = dict(kind="attach_artifact", task=task_id, actor=actor, artifact=artifact_id)
        def apply():
            task = self.state["tasks"].get(task_id)
            artifact = self.state["artifacts"].get(artifact_id)
            if not task or task["assignee"] != actor or task["status"] not in {"accepted", "in_progress"}:
                raise WorldError("Actor cannot attach an artifact to this task")
            if not artifact or artifact["owner"] != actor:
                raise WorldError("Artifact must belong to the task assignee")
            task["artifact"] = artifact_id
            task["status"] = "delivered"
            artifact["history"].append({"kind": "delivered_for_task", "task": task_id})
            return self._record("artifact_delivered", task=task_id, artifact=artifact_id, actor=actor)
        return self._op(operation_id, payload, apply)

    def review_artifact(self, operation_id, reviewer, artifact_id, permission, verdict, comment):
        payload = dict(kind="review_artifact", reviewer=reviewer, artifact=artifact_id, permission=permission,
                       verdict=verdict, comment=comment)
        def apply():
            if not self.has_permission(reviewer, permission):
                raise WorldError("Reviewer lacks permission")
            artifact = self.state["artifacts"].get(artifact_id)
            if not artifact:
                raise WorldError("Unknown artifact")
            if verdict not in {"approve", "revise"} or not isinstance(comment, str) or not comment.strip():
                raise WorldError("Review requires verdict and comment")
            review_id = operation_id
            review = {"id": review_id, "reviewer": reviewer, "artifact": artifact_id, "verdict": verdict, "comment": comment}
            self.state["reviews"][review_id] = review
            artifact["review_status"] = "approved" if verdict == "approve" else "revision_requested"
            artifact["history"].append({"kind": "review", "review": review_id, "verdict": verdict})
            self._record("artifact_reviewed", review=review_id, artifact=artifact_id, reviewer=reviewer, verdict=verdict)
            return review
        return self._op(operation_id, payload, apply)

    def verify_artifact(self, operation_id, verifier, artifact_id, permission):
        payload = dict(kind="verify_artifact", verifier=verifier, artifact=artifact_id, permission=permission)
        def apply():
            if not self.has_permission(verifier, permission):
                raise WorldError("Verifier lacks permission")
            artifact = self.state["artifacts"].get(artifact_id)
            if not artifact or artifact["review_status"] != "approved":
                raise WorldError("Artifact must have approved review before verification")
            artifact["verification_status"] = "verified"
            artifact["history"].append({"kind": "verified", "by": verifier})
            return self._record("artifact_verified", artifact=artifact_id, verifier=verifier)
        return self._op(operation_id, payload, apply)

    def submit_artifact(self, operation_id, submitter, artifact_id, permission=None):
        payload = dict(kind="submit_artifact", submitter=submitter, artifact=artifact_id, permission=permission)
        def apply():
            artifact = self.state["artifacts"].get(artifact_id)
            if not artifact:
                raise WorldError("Unknown artifact")
            if submitter != artifact["owner"] and (not permission or not self.has_permission(submitter, permission)):
                raise WorldError("Submitter lacks authority")
            if artifact["verification_status"] != "verified":
                raise WorldError("Verification required before submission")
            artifact["submission_status"] = "submitted"
            artifact["history"].append({"kind": "submitted", "by": submitter})
            return self._record("artifact_submitted", artifact=artifact_id, submitter=submitter)
        return self._op(operation_id, payload, apply)

    def reserve_task_time(self, operation_id, task_id, slots):
        payload = dict(kind="reserve_task_time", task=task_id, slots=deepcopy(slots))
        def apply():
            task = self.state["tasks"].get(task_id)
            if not task or task["status"] not in {"accepted", "in_progress"}:
                raise WorldError("Task is not active")
            if any(slot.get("actor") != task["assignee"] for slot in slots):
                raise WorldError("Task time must be booked to its assignee")
            ledger = Ledger.restore(self.state["ledger"])
            rows = ledger.reserve(operation_id + ":ledger", slots, f"task {task_id}: {task['title']}")
            self.state["ledger"] = ledger.snapshot()
            task["status"] = "in_progress"
            return rows
        try:
            return self._op(operation_id, payload, apply)
        except LedgerError as exc:
            raise WorldError(str(exc)) from None

    def advance(self, target):
        ledger = Ledger.restore(self.state["ledger"])
        ledger.advance(target)
        self.state["ledger"] = ledger.snapshot()
        self.state["now"] = self.state["ledger"]["now"][:10]
        self._validate()
        return self.snapshot()
