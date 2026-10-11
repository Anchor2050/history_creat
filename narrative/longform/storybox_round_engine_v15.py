"""Round-based StoryBox engine for adaptation-only narrative games.

This module does not generate prose and does not call a model.
It coordinates one narrative game as a sequence of auditable rounds.

The engine separates:
- hard truth from public/private information and actor beliefs;
- one round from one game/arc;
- game convergence from game success;
- world simulation from Storyteller rendering.

Domain-specific actions may be produced by a human, ChatGPT, a local model, or a
future deterministic policy.  This module validates state transitions, records
round debt, and decides whether another round is justified.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any


class RoundEngineError(ValueError):
    pass


ALLOWED_ACTIONS = {
    "inspect",
    "verify",
    "request_information",
    "share_information",
    "withhold_information",
    "contact",
    "move",
    "wait",
    "pass",
    "propose",
    "approve",
    "reject",
    "freeze",
    "resume",
    "escalate",
    "deescalate",
    "allocate",
    "refuse",
    "accuse",
    "correct",
    "protect",
    "document",
}

ROUND_END_REASONS = {
    "all_eligible_actors_resolved",
    "no_legal_actions",
    "deadline_tick",
    "hard_interrupt",
}

GAME_END_REASONS = {
    "objective_resolved",
    "objective_failed",
    "stable_equilibrium",
    "deadlock",
    "absorbed_into_institution",
    "superseded_by_new_game",
    "hard_terminal_event",
    "safety_stop",
    "round_cap",
}

MATERIAL_DELTA_KEYS = {
    "truth",
    "public_information",
    "private_information",
    "beliefs",
    "actor_state",
    "relationships",
    "power",
    "mysteries",
    "map",
    "resources",
    "deadlines",
    "commitments",
    "reputation",
}


@dataclass
class ConvergencePolicy:
    """Quantitative stopping policy for one narrative game."""

    min_rounds: int = 2
    max_rounds: int = 12
    stable_rounds_required: int = 2
    max_zero_delta_rounds: int = 2
    require_objective_or_terminal_for_success: bool = True


@dataclass
class RoundState:
    round_no: int
    eligible_actors: list[str]
    trigger: dict[str, Any]
    reader_clock: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    state_deltas: list[dict[str, Any]] = field(default_factory=list)
    new_questions: list[dict[str, Any]] = field(default_factory=list)
    paid_questions: list[str] = field(default_factory=list)
    map_unlocks: list[str] = field(default_factory=list)
    ended: bool = False
    end_reason: str | None = None


@dataclass
class GameState:
    game_id: str
    objective: dict[str, Any]
    hard_world: dict[str, Any]
    map_state: dict[str, Any]
    actor_state: dict[str, Any]
    truth: dict[str, Any]
    public_information: dict[str, Any]
    private_information: dict[str, Any]
    beliefs: dict[str, Any]
    relationships: dict[str, Any]
    power: dict[str, Any]
    resources: dict[str, Any]
    mysteries: dict[str, Any]
    deadlines: dict[str, Any]
    commitments: dict[str, Any]
    reputation: dict[str, Any]
    payoff_debt: dict[str, Any]
    rounds: list[dict[str, Any]] = field(default_factory=list)
    game_status: str = "active"
    game_end_reason: str | None = None
    successor_game_candidate: dict[str, Any] | None = None
    convergence_policy: ConvergencePolicy = field(default_factory=ConvergencePolicy)



def stable_id(*parts: Any) -> str:
    raw = ":".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]



def _require_mapping(value: Any, name: str):
    if not isinstance(value, dict):
        raise RoundEngineError(f"{name} must be a mapping")



def validate_game_state(game: GameState) -> bool:
    if not game.game_id:
        raise RoundEngineError("game_id is required")
    _require_mapping(game.objective, "objective")
    if not game.objective.get("question"):
        raise RoundEngineError("objective.question is required")
    if game.game_status not in {"active", "ended"}:
        raise RoundEngineError("unsupported game_status")
    if game.convergence_policy.min_rounds < 1:
        raise RoundEngineError("min_rounds must be >=1")
    if game.convergence_policy.max_rounds < game.convergence_policy.min_rounds:
        raise RoundEngineError("max_rounds must be >= min_rounds")
    if game.convergence_policy.stable_rounds_required < 1:
        raise RoundEngineError("stable_rounds_required must be >=1")
    return True



def build_round_request(game: GameState, trigger: dict[str, Any], eligible_actors: list[str]) -> dict[str, Any]:
    """Build a model-agnostic request for one round.

    Only actor-local visible information is exposed. Truth remains backstage unless
    a fact is public or privately known to the actor.
    """
    validate_game_state(game)
    if game.game_status != "active":
        raise RoundEngineError("cannot build a round for an ended game")

    unknown = [a for a in eligible_actors if a not in game.actor_state]
    if unknown:
        raise RoundEngineError(f"unknown eligible actors: {unknown}")

    round_no = len(game.rounds) + 1
    actors = {}
    for actor_id in eligible_actors:
        actors[actor_id] = {
            "state": deepcopy(game.actor_state.get(actor_id, {})),
            "private_information": deepcopy(game.private_information.get(actor_id, {})),
            "beliefs": deepcopy(game.beliefs.get(actor_id, {})),
            "relationships": deepcopy(game.relationships.get(actor_id, {})),
            "power": deepcopy(game.power.get(actor_id, {})),
            "resources": deepcopy(game.resources.get(actor_id, {})),
            "public_information": deepcopy(game.public_information),
            "reachable_map": deepcopy(game.map_state.get("reachable_by_actor", {}).get(actor_id, [])),
            "deadlines": deepcopy(game.deadlines),
            "commitments": deepcopy(game.commitments.get(actor_id, {})),
            "reputation": deepcopy(game.reputation.get(actor_id, {})),
        }

    return {
        "request_version": 1,
        "game_id": game.game_id,
        "round_no": round_no,
        "objective": deepcopy(game.objective),
        "trigger": deepcopy(trigger),
        "eligible_actors": list(eligible_actors),
        "actors": actors,
        "open_mysteries": deepcopy(game.mysteries),
        "payoff_debt": deepcopy(game.payoff_debt),
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "rules": [
            "act only on information visible to the actor",
            "actor beliefs may be wrong without being irrational",
            "formal power and factual knowledge are separate",
            "doing nothing or passing is legal",
            "do not invent access, authority, money, data, relationships, or evidence",
            "an action proposal is not yet a world outcome",
        ],
    }



def validate_round_actions(request: dict[str, Any], actions: list[dict[str, Any]]) -> bool:
    eligible = set(request["eligible_actors"])
    seen_action_ids = set()
    for row in actions:
        actor = row.get("actor")
        if actor not in eligible:
            raise RoundEngineError(f"action actor not eligible: {actor}")
        if row.get("action") not in ALLOWED_ACTIONS:
            raise RoundEngineError(f"unsupported action: {row.get('action')}")
        if not row.get("action_id"):
            raise RoundEngineError("action_id is required")
        if row["action_id"] in seen_action_ids:
            raise RoundEngineError("duplicate action_id")
        seen_action_ids.add(row["action_id"])
        if "basis" not in row:
            raise RoundEngineError("action basis is required")
    return True



def validate_round_resolution(request: dict[str, Any], resolution: dict[str, Any]) -> bool:
    """Validate a resolved round produced by hard-world logic or an external backend."""
    if resolution.get("game_id") != request["game_id"]:
        raise RoundEngineError("resolution game_id mismatch")
    if resolution.get("round_no") != request["round_no"]:
        raise RoundEngineError("resolution round_no mismatch")
    if resolution.get("end_reason") not in ROUND_END_REASONS:
        raise RoundEngineError("unsupported round end reason")

    validate_round_actions(request, resolution.get("actions", []))

    for delta in resolution.get("state_deltas", []):
        if delta.get("domain") not in MATERIAL_DELTA_KEYS:
            raise RoundEngineError(f"unsupported state delta domain: {delta.get('domain')}")
        if "value" not in delta:
            raise RoundEngineError("state delta requires value")
        if not delta.get("evidence"):
            raise RoundEngineError("state delta requires evidence")

    for question in resolution.get("new_questions", []):
        if not question.get("question_id") or not question.get("question"):
            raise RoundEngineError("new mystery question is malformed")

    return True



def _set_path(mapping: dict[str, Any], path: list[str], value: Any):
    target = mapping
    for key in path[:-1]:
        target = target.setdefault(key, {})
        if not isinstance(target, dict):
            raise RoundEngineError("state delta path crosses non-mapping value")
    target[path[-1]] = deepcopy(value)



def _state_domain(game: GameState, domain: str) -> dict[str, Any]:
    return getattr(game, domain)



def apply_round_resolution(game: GameState, request: dict[str, Any], resolution: dict[str, Any]) -> GameState:
    """Apply one resolved round and return a deep-copied new game state."""
    validate_game_state(game)
    validate_round_resolution(request, resolution)
    nxt = deepcopy(game)

    for delta in resolution.get("state_deltas", []):
        domain = delta["domain"]
        target = _state_domain(nxt, domain)
        path = delta.get("path", [])
        if not path:
            if not isinstance(delta["value"], dict):
                raise RoundEngineError("whole-domain replacement requires a mapping")
            setattr(nxt, domain, deepcopy(delta["value"]))
        else:
            _set_path(target, path, delta["value"])

    for qid in resolution.get("paid_questions", []):
        if qid in nxt.mysteries:
            nxt.mysteries[qid]["status"] = "paid_or_transformed"
        if qid in nxt.payoff_debt:
            nxt.payoff_debt[qid]["status"] = "paid_or_transformed"

    for row in resolution.get("new_questions", []):
        qid = row["question_id"]
        if qid in nxt.mysteries:
            raise RoundEngineError(f"duplicate mystery question: {qid}")
        nxt.mysteries[qid] = deepcopy(row)
        nxt.mysteries[qid].setdefault("status", "open")

    for node in resolution.get("map_unlocks", []):
        unlocked = nxt.map_state.setdefault("unlocked", [])
        if node not in unlocked:
            unlocked.append(node)

    round_record = {
        "round_no": request["round_no"],
        "trigger": deepcopy(request["trigger"]),
        "eligible_actors": list(request["eligible_actors"]),
        "actions": deepcopy(resolution.get("actions", [])),
        "state_deltas": deepcopy(resolution.get("state_deltas", [])),
        "paid_questions": list(resolution.get("paid_questions", [])),
        "new_questions": deepcopy(resolution.get("new_questions", [])),
        "map_unlocks": list(resolution.get("map_unlocks", [])),
        "end_reason": resolution["end_reason"],
        "material_delta_score": material_delta_score(resolution),
        "notes": deepcopy(resolution.get("notes", [])),
    }
    nxt.rounds.append(round_record)
    return nxt



def material_delta_score(resolution: dict[str, Any]) -> int:
    """Count narratively material state changes in one resolved round."""
    score = 0
    score += len(resolution.get("state_deltas", []))
    score += len(resolution.get("paid_questions", []))
    score += len(resolution.get("new_questions", []))
    score += len(resolution.get("map_unlocks", []))
    return score



def unresolved_objective(game: GameState) -> bool:
    status = game.objective.get("status", "open")
    return status not in {"resolved", "failed", "absorbed", "superseded"}



def _recent_delta_scores(game: GameState, n: int) -> list[int]:
    if n <= 0:
        return []
    return [int(row.get("material_delta_score", 0)) for row in game.rounds[-n:]]



def _has_active_deadline(game: GameState) -> bool:
    for row in game.deadlines.values():
        if isinstance(row, dict) and row.get("status", "active") == "active":
            return True
    return False



def _has_open_actionable_mystery(game: GameState) -> bool:
    for row in game.mysteries.values():
        if row.get("status", "open") != "open":
            continue
        if row.get("actionable", True):
            return True
    return False



def evaluate_game_convergence(game: GameState) -> dict[str, Any]:
    """Decide whether the current game should continue, converge, deadlock, or spawn a new game.

    Convergence does not mean success.  A game may end in deadlock, institutional
    absorption, failure, or a transition to a successor game.
    """
    validate_game_state(game)
    rounds = len(game.rounds)
    policy = game.convergence_policy

    objective_status = game.objective.get("status", "open")
    if objective_status == "resolved":
        return {"continue": False, "converged": True, "reason": "objective_resolved"}
    if objective_status == "failed":
        return {"continue": False, "converged": True, "reason": "objective_failed"}
    if objective_status == "absorbed":
        return {"continue": False, "converged": True, "reason": "absorbed_into_institution"}
    if objective_status == "superseded":
        return {"continue": False, "converged": True, "reason": "superseded_by_new_game"}

    if game.successor_game_candidate and game.successor_game_candidate.get("ready"):
        return {
            "continue": False,
            "converged": True,
            "reason": "superseded_by_new_game",
            "successor_game_candidate": deepcopy(game.successor_game_candidate),
        }

    if rounds >= policy.max_rounds:
        return {"continue": False, "converged": False, "reason": "round_cap"}

    if rounds < policy.min_rounds:
        return {"continue": True, "converged": False, "reason": "minimum_rounds_not_reached"}

    stable_scores = _recent_delta_scores(game, policy.stable_rounds_required)
    if len(stable_scores) == policy.stable_rounds_required and all(x == 0 for x in stable_scores):
        if unresolved_objective(game):
            if _has_active_deadline(game) or _has_open_actionable_mystery(game):
                return {
                    "continue": False,
                    "converged": False,
                    "reason": "deadlock",
                    "note": "Live pressure remains but recent rounds produced no material state change.",
                }
            return {
                "continue": False,
                "converged": True,
                "reason": "stable_equilibrium",
                "note": "No material state change and no active pressure justifies another round.",
            }

    zero_scores = _recent_delta_scores(game, policy.max_zero_delta_rounds)
    if len(zero_scores) == policy.max_zero_delta_rounds and all(x == 0 for x in zero_scores):
        return {
            "continue": False,
            "converged": False,
            "reason": "deadlock",
            "note": "Repeated zero-delta rounds are not allowed to become filler.",
        }

    return {"continue": True, "converged": False, "reason": "material_state_still_moving"}



def close_game(game: GameState, evaluation: dict[str, Any]) -> GameState:
    reason = evaluation.get("reason")
    if reason not in GAME_END_REASONS:
        raise RoundEngineError(f"unsupported game end reason: {reason}")
    nxt = deepcopy(game)
    nxt.game_status = "ended"
    nxt.game_end_reason = reason
    return nxt



def successor_game_seed(game: GameState, *, game_id: str, question: str, trigger: dict[str, Any]) -> dict[str, Any]:
    """Carry durable state into a new game while changing the main objective.

    The new game inherits personality/relationship/reputation/information debt but
    does not automatically inherit every actor or map node as active.
    """
    if game.game_status != "ended":
        raise RoundEngineError("successor seed requires a closed game")
    return {
        "game_id": game_id,
        "objective": {"question": question, "status": "open"},
        "trigger": deepcopy(trigger),
        "carry": {
            "actor_state": deepcopy(game.actor_state),
            "relationships": deepcopy(game.relationships),
            "reputation": deepcopy(game.reputation),
            "beliefs": deepcopy(game.beliefs),
            "public_information": deepcopy(game.public_information),
            "private_information": deepcopy(game.private_information),
            "commitments": deepcopy(game.commitments),
            "unpaid_payoff_debt": {
                k: deepcopy(v)
                for k, v in game.payoff_debt.items()
                if v.get("status", "open") == "open"
            },
        },
    }
