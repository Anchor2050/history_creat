"""Backend-neutral cognition protocol for the chatbot-led StoryBox branch.

The repository owns state, evidence and validation. A cognition backend only
proposes structured semantic output. The default backend can be the current
ChatGPT product conversation; DeepSeek or a local model may implement the same
``json(instruction, state)`` interface later.

No backend is allowed to commit world facts directly.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping


TASK_KINDS = {
    "micro_replay",
    "personal_reflection",
    "behavior_decision",
    "storyteller_analysis",
}

BACKEND_NAMES = {
    "chatgpt_product_conversation",
    "deepseek_api",
    "local_model",
    "deterministic_control",
}


class CognitionProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class CognitionTask:
    task_id: str
    kind: str
    instruction: str
    payload: dict[str, Any]
    output_schema: dict[str, Any]
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "instruction": self.instruction,
            "payload": deepcopy(self.payload),
            "output_schema": deepcopy(self.output_schema),
            "evidence_refs": list(self.evidence_refs),
        }


def build_task(*, task_id: str, kind: str, instruction: str,
               payload: Mapping[str, Any], output_schema: Mapping[str, Any],
               evidence_refs=()) -> dict[str, Any]:
    if not task_id or not isinstance(task_id, str):
        raise CognitionProtocolError("task_id must be a non-empty string")
    if kind not in TASK_KINDS:
        raise CognitionProtocolError(f"unsupported cognition task kind: {kind}")
    if not instruction or not isinstance(instruction, str):
        raise CognitionProtocolError("instruction must be a non-empty string")
    if not isinstance(payload, Mapping) or not isinstance(output_schema, Mapping):
        raise CognitionProtocolError("payload/output_schema must be mappings")
    refs = tuple(str(ref) for ref in evidence_refs)
    return CognitionTask(
        task_id=task_id,
        kind=kind,
        instruction=instruction,
        payload=dict(payload),
        output_schema=dict(output_schema),
        evidence_refs=refs,
    ).as_dict()


def validate_common_result(task: Mapping[str, Any], result: Mapping[str, Any], *, backend: str) -> dict[str, Any]:
    if backend not in BACKEND_NAMES:
        raise CognitionProtocolError(f"unsupported backend: {backend}")
    if not isinstance(result, Mapping):
        raise CognitionProtocolError("cognition result must be a mapping")
    if result.get("task_id") != task.get("task_id"):
        raise CognitionProtocolError("result task_id does not match task")
    if result.get("kind") != task.get("kind"):
        raise CognitionProtocolError("result kind does not match task")

    known_refs = set(task.get("evidence_refs", []))
    used_refs = set(result.get("evidence_refs", []))
    if not used_refs.issubset(known_refs):
        extra = sorted(used_refs - known_refs)
        raise CognitionProtocolError(f"result cites evidence not supplied to backend: {extra}")

    validated = deepcopy(dict(result))
    validated["backend"] = backend
    validated["validated_against_task"] = True
    return validated


def run_with_json_provider(task: Mapping[str, Any], provider, *, backend: str) -> dict[str, Any]:
    """Run the same structured task through DeepSeek/local adapters.

    ``provider`` deliberately uses the tiny existing contract
    ``provider.json(instruction, state)``. This works with narrative.providers.DeepSeek
    and can be implemented by an Ollama/local adapter without changing task schema.
    The current ChatGPT product conversation does not call this function: it reads the
    task from GitHub and writes a result back through the connector.
    """
    response = provider.json(
        task["instruction"],
        {
            "task_id": task["task_id"],
            "kind": task["kind"],
            "payload": task["payload"],
            "output_schema": task["output_schema"],
            "allowed_evidence_refs": task.get("evidence_refs", []),
        },
    )
    response.setdefault("task_id", task["task_id"])
    response.setdefault("kind", task["kind"])
    response.setdefault("evidence_refs", [])
    return validate_common_result(task, response, backend=backend)
