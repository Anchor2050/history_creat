"""Scene-aware, concurrent multi-game StoryBox runtime.

This adaptation-only runtime sits above ``storybox_round_engine_v15``.
It does not generate prose and does not call a model.

Hierarchy:
    World -> EventArc -> Game -> Scene -> Round -> Action

Key additions:
- several rounds may occur inside one scene;
- several games may be active inside one event arc;
- one actor may participate in several games at once;
- actor stance/role is local to a game, never a global moral label;
- cross-game spillover is explicit rather than automatic;
- event nodes fire only after auditable predicates are satisfied.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


class MultiGameEngineError(ValueError):
    pass


SCENE_END_REASONS = {
    "local_objective_resolved",
    "local_objective_transformed",
    "new_evidence_changes_action_set",
    "authority_changed",
    "deadline_interrupt",
    "all_local_actors_resolved",
    "local_deadlock",
    "participants_separated",
    "hard_interrupt",
}

GAME_STATUSES = {"active", "resolved", "failed", "deadlock", "absorbed", "superseded"}
EVENT_NODE_STATUSES = {"locked", "ready", "fired", "cancelled"}

SPILLOVER_DOMAINS = {
    "fatigue",
    "reputation",
    "commitments",
    "resources",
    "relationships",
    "formal_power",
    "public_information",
    "deadlines",
    "world_rules",
}


@dataclass
class GameParticipation:
    game_id: str
    local_role: str
    local_stake: str
    stance: str
    attention: float
    authority: float = 0.0
    risk_exposure: float = 0.0
    obligations: list[str] = field(default_factory=list)
    confidential_information: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass
class ActorPortfolio:
    actor_id: str
    attention_budget: float = 1.0
    coordination_capacity: float = 0.5
    delegation_capacity: float = 0.3
    formal_power: float = 0.3
    information_access: float = 0.3
    stress_tolerance: float = 0.5
    current_fatigue: float = 0.0
    max_parallel_games_soft: int = 1
    max_parallel_games_hard: int = 2
    overload_penalty_per_slot: float = 0.10
    participations: dict[str, GameParticipation] = field(default_factory=dict)


@dataclass
class SceneState:
    scene_id: str
    event_arc_id: str
    game_id: str
    trigger: dict[str, Any]
    location: str | None
    channel: str | None
    participants: list[str]
    observers: list[str] = field(default_factory=list)
    local_objectives: list[str] = field(default_factory=list)
    information_boundaries: dict[str, Any] = field(default_factory=dict)
    rounds: list[dict[str, Any]] = field(default_factory=list)
    outcome_deltas: list[dict[str, Any]] = field(default_factory=list)
    unresolved_carry: list[str] = field(default_factory=list)
    status: str = "active"
    end_reason: str | None = None


@dataclass
class GameRuntime:
    game_id: str
    event_arc_id: str
    objective: str
    status: str = "active"
    scene_ids: list[str] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    local_state: dict[str, Any] = field(default_factory=dict)
    output_bridges: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EventNode:
    node_id: str
    description: str
    predicates: list[dict[str, Any]]
    status: str = "locked"
    fires_world_deltas: list[dict[str, Any]] = field(default_factory=list)
    opens_games: list[str] = field(default_factory=list)
    closes_games: list[str] = field(default_factory=list)


@dataclass
class EventArcState:
    event_arc_id: str
    games: dict[str, GameRuntime]
    scenes: dict[str, SceneState]
    event_nodes: dict[str, EventNode]
    fired_nodes: list[str] = field(default_factory=list)
    arc_state: dict[str, Any] = field(default_factory=dict)
    status: str = "active"


@dataclass
class MultiGameWorldState:
    actor_portfolios: dict[str, ActorPortfolio]
    event_arcs: dict[str, EventArcState]
    global_state: dict[str, Any] = field(default_factory=dict)
    spillover_history: list[dict[str, Any]] = field(default_factory=list)


def _active_participations(portfolio: ActorPortfolio) -> list[GameParticipation]:
    return [p for p in portfolio.participations.values() if p.status == "active"]


def validate_actor_portfolio(portfolio: ActorPortfolio) -> bool:
    if not portfolio.actor_id:
        raise MultiGameEngineError("actor_id is required")
    if portfolio.attention_budget <= 0:
        raise MultiGameEngineError("attention_budget must be positive")
    if portfolio.max_parallel_games_soft < 1:
        raise MultiGameEngineError("soft game cap must be >= 1")
    if portfolio.max_parallel_games_hard < portfolio.max_parallel_games_soft:
        raise MultiGameEngineError("hard game cap must be >= soft game cap")
    if not (0 <= portfolio.current_fatigue <= 1.5):
        raise MultiGameEngineError("current_fatigue outside supported range")
    for p in portfolio.participations.values():
        if p.attention < 0:
            raise MultiGameEngineError("participation attention must be >= 0")
    return True


def participation_load(portfolio: ActorPortfolio) -> dict[str, Any]:
    validate_actor_portfolio(portfolio)
    active = _active_participations(portfolio)
    attention = sum(p.attention for p in active)
    count = len(active)
    soft_overflow = max(0, count - portfolio.max_parallel_games_soft)
    attention_overflow = max(0.0, attention - portfolio.attention_budget)
    return {
        "active_game_count": count,
        "attention_used": attention,
        "attention_budget": portfolio.attention_budget,
        "soft_game_overflow": soft_overflow,
        "attention_overflow": attention_overflow,
        "hard_cap_remaining": max(0, portfolio.max_parallel_games_hard - count),
    }


def join_game(portfolio: ActorPortfolio, participation: GameParticipation) -> ActorPortfolio:
    """Return a copied portfolio with one new game participation.

    Crossing the soft cap is legal and produces fatigue. Crossing the hard cap is
    illegal. Attention overflow is also legal up to the hard cap but adds fatigue.
    """
    validate_actor_portfolio(portfolio)
    nxt = deepcopy(portfolio)
    existing = nxt.participations.get(participation.game_id)
    if existing and existing.status == "active":
        raise MultiGameEngineError("actor already participates in this game")

    active_count = len(_active_participations(nxt))
    if active_count + 1 > nxt.max_parallel_games_hard:
        raise MultiGameEngineError("hard parallel-game cap exceeded")

    nxt.participations[participation.game_id] = deepcopy(participation)
    load = participation_load(nxt)
    overload = load["soft_game_overflow"] + load["attention_overflow"]
    if overload > 0:
        # Parameterized rather than role-labelled: high-capacity actors can absorb
        # more concurrency because their budgets/caps are larger.
        fatigue_delta = nxt.overload_penalty_per_slot * overload
        mitigation = 0.35 * nxt.delegation_capacity + 0.20 * nxt.coordination_capacity
        nxt.current_fatigue = min(1.5, nxt.current_fatigue + max(0.0, fatigue_delta * (1 - mitigation)))
    return nxt


def leave_game(portfolio: ActorPortfolio, game_id: str) -> ActorPortfolio:
    nxt = deepcopy(portfolio)
    if game_id not in nxt.participations:
        raise MultiGameEngineError("actor is not registered in game")
    nxt.participations[game_id].status = "closed"
    return nxt


def validate_scene(scene: SceneState, arc: EventArcState, world: MultiGameWorldState) -> bool:
    if scene.status not in {"active", "ended"}:
        raise MultiGameEngineError("unsupported scene status")
    if scene.event_arc_id != arc.event_arc_id:
        raise MultiGameEngineError("scene event_arc_id mismatch")
    if scene.game_id not in arc.games:
        raise MultiGameEngineError("scene references unknown game")
    if len(set(scene.participants)) != len(scene.participants):
        raise MultiGameEngineError("duplicate scene participant")
    unknown = [a for a in scene.participants if a not in world.actor_portfolios]
    if unknown:
        raise MultiGameEngineError(f"unknown scene participants: {unknown}")
    for actor_id in scene.participants:
        p = world.actor_portfolios[actor_id].participations.get(scene.game_id)
        if not p or p.status != "active":
            raise MultiGameEngineError(f"scene participant lacks active game participation: {actor_id}")
    if scene.status == "ended" and scene.end_reason not in SCENE_END_REASONS:
        raise MultiGameEngineError("ended scene needs supported end_reason")
    return True


def append_round_to_scene(scene: SceneState, round_record: dict[str, Any]) -> SceneState:
    if scene.status != "active":
        raise MultiGameEngineError("cannot append round to ended scene")
    if not isinstance(round_record, dict) or not round_record.get("round_no"):
        raise MultiGameEngineError("round_record requires round_no")
    nxt = deepcopy(scene)
    expected = len(nxt.rounds) + 1
    if int(round_record["round_no"]) != expected:
        raise MultiGameEngineError("scene round number must be contiguous")
    nxt.rounds.append(deepcopy(round_record))
    return nxt


def end_scene(
    scene: SceneState,
    *,
    reason: str,
    outcome_deltas: list[dict[str, Any]] | None = None,
    unresolved_carry: list[str] | None = None,
) -> SceneState:
    if reason not in SCENE_END_REASONS:
        raise MultiGameEngineError("unsupported scene end reason")
    nxt = deepcopy(scene)
    nxt.status = "ended"
    nxt.end_reason = reason
    nxt.outcome_deltas = deepcopy(outcome_deltas or [])
    nxt.unresolved_carry = list(unresolved_carry or [])
    return nxt


def register_scene(world: MultiGameWorldState, scene: SceneState) -> MultiGameWorldState:
    if scene.event_arc_id not in world.event_arcs:
        raise MultiGameEngineError("unknown event arc")
    nxt = deepcopy(world)
    arc = nxt.event_arcs[scene.event_arc_id]
    validate_scene(scene, arc, nxt)
    if scene.scene_id in arc.scenes:
        raise MultiGameEngineError("duplicate scene_id")
    arc.scenes[scene.scene_id] = deepcopy(scene)
    game = arc.games[scene.game_id]
    game.scene_ids.append(scene.scene_id)
    return nxt


def apply_cross_game_spillover(
    world: MultiGameWorldState,
    *,
    actor_id: str,
    source_game_id: str,
    target_game_id: str,
    domain: str,
    value: Any,
    bridge: str,
    evidence: str,
) -> MultiGameWorldState:
    """Apply an explicit cross-game state bridge.

    Local facts do not synchronize automatically. A spillover needs a bridge such
    as public disclosure, a shared report, personal memory, resource transfer or
    formal authority decision.
    """
    if domain not in SPILLOVER_DOMAINS:
        raise MultiGameEngineError("unsupported spillover domain")
    if not bridge or not evidence:
        raise MultiGameEngineError("spillover requires bridge and evidence")
    if actor_id not in world.actor_portfolios:
        raise MultiGameEngineError("unknown spillover actor")
    portfolio = world.actor_portfolios[actor_id]
    for gid in (source_game_id, target_game_id):
        p = portfolio.participations.get(gid)
        if not p or p.status != "active":
            raise MultiGameEngineError("actor must actively participate in both games for personal spillover")

    nxt = deepcopy(world)
    key = f"{actor_id}:{target_game_id}:{domain}"
    nxt.global_state.setdefault("cross_game", {})[key] = deepcopy(value)
    nxt.spillover_history.append({
        "actor_id": actor_id,
        "source_game_id": source_game_id,
        "target_game_id": target_game_id,
        "domain": domain,
        "value": deepcopy(value),
        "bridge": bridge,
        "evidence": evidence,
    })
    return nxt


def _read_path(context: dict[str, Any], path: list[str]) -> Any:
    cur: Any = context
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def evaluate_predicate(context: dict[str, Any], predicate: dict[str, Any]) -> bool:
    """Evaluate a small auditable predicate language for event-node triggers."""
    path = predicate.get("path")
    op = predicate.get("op")
    target = predicate.get("value")
    if not isinstance(path, list) or not path:
        raise MultiGameEngineError("predicate.path must be a non-empty list")
    actual = _read_path(context, path)

    if op == "eq":
        return actual == target
    if op == "ne":
        return actual != target
    if op == "in":
        return actual in target if isinstance(target, list) else False
    if op == "contains":
        return target in actual if isinstance(actual, (list, set, tuple, str)) else False
    if op == "gte":
        return actual is not None and actual >= target
    if op == "lte":
        return actual is not None and actual <= target
    if op == "truthy":
        return bool(actual)
    if op == "falsy":
        return not bool(actual)
    raise MultiGameEngineError(f"unsupported predicate op: {op}")


def event_node_context(world: MultiGameWorldState, arc: EventArcState) -> dict[str, Any]:
    return {
        "world": deepcopy(world.global_state),
        "arc": deepcopy(arc.arc_state),
        "games": {
            gid: {
                "status": game.status,
                "local_state": deepcopy(game.local_state),
                "scene_count": len(game.scene_ids),
            }
            for gid, game in arc.games.items()
        },
        "fired_nodes": list(arc.fired_nodes),
    }


def evaluate_event_node(world: MultiGameWorldState, event_arc_id: str, node_id: str) -> dict[str, Any]:
    if event_arc_id not in world.event_arcs:
        raise MultiGameEngineError("unknown event arc")
    arc = world.event_arcs[event_arc_id]
    if node_id not in arc.event_nodes:
        raise MultiGameEngineError("unknown event node")
    node = arc.event_nodes[node_id]
    if node.status in {"fired", "cancelled"}:
        return {"ready": False, "status": node.status, "failed_predicates": []}
    context = event_node_context(world, arc)
    failed = [p for p in node.predicates if not evaluate_predicate(context, p)]
    return {
        "ready": not failed,
        "status": "ready" if not failed else "locked",
        "failed_predicates": deepcopy(failed),
    }


def _set_path(mapping: dict[str, Any], path: list[str], value: Any):
    if not path:
        raise MultiGameEngineError("world delta path cannot be empty")
    target = mapping
    for key in path[:-1]:
        target = target.setdefault(key, {})
        if not isinstance(target, dict):
            raise MultiGameEngineError("world delta path crosses non-mapping")
    target[path[-1]] = deepcopy(value)


def fire_event_node(world: MultiGameWorldState, event_arc_id: str, node_id: str) -> MultiGameWorldState:
    result = evaluate_event_node(world, event_arc_id, node_id)
    if not result["ready"]:
        raise MultiGameEngineError("event node preconditions are not satisfied")

    nxt = deepcopy(world)
    arc = nxt.event_arcs[event_arc_id]
    node = arc.event_nodes[node_id]
    node.status = "fired"
    arc.fired_nodes.append(node_id)

    for delta in node.fires_world_deltas:
        path = delta.get("path")
        if not isinstance(path, list) or not path:
            raise MultiGameEngineError("event-node world delta requires path")
        _set_path(nxt.global_state, path, delta.get("value"))

    for gid in node.closes_games:
        if gid in arc.games and arc.games[gid].status == "active":
            arc.games[gid].status = "superseded"
    for gid in node.opens_games:
        if gid not in arc.games:
            raise MultiGameEngineError(f"event node opens unknown game: {gid}")
        if arc.games[gid].status != "active":
            arc.games[gid].status = "active"
    return nxt


def game_local_role(world: MultiGameWorldState, actor_id: str, game_id: str) -> dict[str, Any]:
    """Return the actor's local role without inferring global moral character."""
    if actor_id not in world.actor_portfolios:
        raise MultiGameEngineError("unknown actor")
    p = world.actor_portfolios[actor_id].participations.get(game_id)
    if not p:
        raise MultiGameEngineError("actor has no participation in game")
    return {
        "local_role": p.local_role,
        "local_stake": p.local_stake,
        "stance": p.stance,
        "authority": p.authority,
        "risk_exposure": p.risk_exposure,
        "obligations": list(p.obligations),
    }
