"""Adapter between TextArena SecretMafia observations and StoryBox SCK v0.

This file intentionally does not import TextArena.  It consumes a small visible
state dictionary so the same adapter can be used against a live TextArena env,
recorded logs, or unit-test fixtures.

TextArena SecretMafia phases currently include Night-Mafia, Night-Doctor,
Night-Detective, Day-Discussion and Day-Voting.  Structured night/vote actions
are encoded as ``[Player X]``; discussion remains a separate language-rendering
step after SCK has selected a communication intent.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re
from typing import Any, Iterable, Mapping, Sequence

from .storybox_sck_v0 import (
    BeliefState,
    CommunicationIntent,
    EvidenceRecord,
    SCKError,
    StrategicDecision,
    StrategicObservation,
)


PHASE_NIGHT_MAFIA = "Night-Mafia"
PHASE_NIGHT_DOCTOR = "Night-Doctor"
PHASE_NIGHT_DETECTIVE = "Night-Detective"
PHASE_DAY_DISCUSSION = "Day-Discussion"
PHASE_DAY_VOTING = "Day-Voting"
TARGET_PHASES = {
    PHASE_NIGHT_MAFIA,
    PHASE_NIGHT_DOCTOR,
    PHASE_NIGHT_DETECTIVE,
    PHASE_DAY_VOTING,
}


def mafia_world_id(mafia_players: Iterable[int]) -> str:
    members = sorted(set(int(x) for x in mafia_players))
    return "mafia={" + ",".join(map(str, members)) + "}"


def parse_mafia_world(world_id: str) -> frozenset[int]:
    match = re.fullmatch(r"mafia=\{([0-9,]*)\}", world_id)
    if not match:
        raise SCKError(f"invalid mafia world id: {world_id}")
    body = match.group(1)
    if not body:
        return frozenset()
    return frozenset(int(x) for x in body.split(","))


def initial_mafia_world_belief(
    *,
    num_players: int,
    actor_id: int,
    actor_role: str,
    mafia_count: int,
    known_mafia: Sequence[int] = (),
    impossible_mafia: Sequence[int] = (),
) -> BeliefState:
    """Enumerate hidden-role worlds consistent with the actor's private info."""
    if not 6 <= num_players <= 15:
        raise SCKError("SecretMafia supports 6-15 players")
    if mafia_count < 1 or mafia_count >= num_players:
        raise SCKError("invalid mafia count")

    all_players = set(range(num_players))
    known = set(map(int, known_mafia))
    impossible = set(map(int, impossible_mafia))
    if known & impossible:
        raise SCKError("a player cannot be both known and impossible mafia")

    role = actor_role.lower()
    if role == "mafia":
        known.add(actor_id)
    else:
        impossible.add(actor_id)

    if len(known) > mafia_count:
        raise SCKError("known mafia exceeds configured mafia count")

    candidates = sorted(all_players - known - impossible)
    missing = mafia_count - len(known)
    worlds = {}
    for extra in combinations(candidates, missing):
        world = known | set(extra)
        worlds[mafia_world_id(world)] = 1.0
    if not worlds:
        raise SCKError("private information leaves no feasible hidden worlds")
    return BeliefState(worlds)


def evidence_from_known_alignment(
    *,
    evidence_id: str,
    source: str,
    target_player: int,
    is_mafia: bool,
    current_belief: BeliefState,
    reliability: float = 1.0,
    description: str = "",
) -> EvidenceRecord:
    """Create hard/soft role evidence without exposing any unobserved truth."""
    ratios = {}
    for world_id in current_belief.hypotheses:
        world = parse_mafia_world(world_id)
        agrees = (target_player in world) == bool(is_mafia)
        # 1e6 is strong enough to emulate near-hard exclusion while preserving
        # numerical stability and an auditable likelihood-ratio update.
        ratios[world_id] = 1e6 if agrees else 1e-6
    return EvidenceRecord(
        evidence_id=evidence_id,
        source=source,
        likelihood_ratio_by_hypothesis=ratios,
        reliability=reliability,
        informative=True,
        description=description or f"Player {target_player} alignment evidence",
    )


def evidence_from_behavior_signal(
    *,
    evidence_id: str,
    source: str,
    target_player: int,
    mafia_likelihood_ratio: float,
    current_belief: BeliefState,
    reliability: float,
    description: str,
) -> EvidenceRecord:
    """Encode an explicitly supplied behavioral likelihood ratio.

    The adapter never decides by itself that an accusation, silence, or vote is
    suspicious.  An external evidence model must supply the likelihood ratio;
    this prevents brittle hard-coded social stereotypes from becoming truth.
    """
    if mafia_likelihood_ratio <= 0:
        raise SCKError("behavior likelihood ratio must be positive")
    ratios = {}
    for world_id in current_belief.hypotheses:
        world = parse_mafia_world(world_id)
        ratios[world_id] = mafia_likelihood_ratio if target_player in world else 1.0
    return EvidenceRecord(
        evidence_id=evidence_id,
        source=source,
        likelihood_ratio_by_hypothesis=ratios,
        reliability=reliability,
        informative=True,
        description=description,
    )


def marginal_mafia_probabilities(belief: BeliefState, num_players: int) -> dict[int, float]:
    out = {player: 0.0 for player in range(num_players)}
    for world_id, probability in belief.hypotheses.items():
        for player in parse_mafia_world(world_id):
            if player in out:
                out[player] += probability
    return out


@dataclass(frozen=True)
class SecretMafiaVisibleState:
    actor_id: int
    num_players: int
    phase: str
    day_number: int
    alive_players: Sequence[int]
    actor_role: str
    public_messages: Sequence[Mapping[str, Any]] = ()
    private_messages: Sequence[Mapping[str, Any]] = ()
    known_mafia: Sequence[int] = ()
    investigations: Mapping[int, bool] | None = None
    pending_elimination: int | None = None
    discussion_round_index: int | None = None


class TextArenaSecretMafiaAdapter:
    def __init__(self, game_id: str = "textarena:secret-mafia"):
        self.game_id = game_id

    @staticmethod
    def _target_actions(state: SecretMafiaVisibleState) -> list[dict[str, Any]]:
        actor = state.actor_id
        alive = list(map(int, state.alive_players))
        role = state.actor_role.lower()
        if state.phase == PHASE_NIGHT_MAFIA:
            invalid = set(state.known_mafia) | {actor}
            targets = [p for p in alive if p not in invalid]
            action_kind = "mafia_eliminate"
        elif state.phase == PHASE_NIGHT_DOCTOR:
            targets = [p for p in alive if p != actor]
            action_kind = "protect"
        elif state.phase == PHASE_NIGHT_DETECTIVE:
            targets = [p for p in alive if p != actor]
            action_kind = "investigate"
        elif state.phase == PHASE_DAY_VOTING:
            targets = [p for p in alive if p != actor]
            action_kind = "vote"
        else:
            return []
        return [
            {
                "action_id": f"{action_kind}:{target}",
                "kind": action_kind,
                "target": target,
                "textarena_action": f"[Player {target}]",
            }
            for target in targets
        ]

    def to_strategic_observation(self, state: SecretMafiaVisibleState) -> StrategicObservation:
        if state.actor_id not in state.alive_players:
            raise SCKError("eliminated actor cannot receive a live SecretMafia turn")

        if state.phase == PHASE_DAY_DISCUSSION:
            legal_actions = [
                {
                    "action_id": "communicate:public",
                    "kind": "communicate",
                    "channel": "public_discussion",
                },
                {
                    "action_id": "communicate:minimal",
                    "kind": "communicate",
                    "channel": "public_discussion",
                    "constraint": "minimal_disclosure",
                },
            ]
        elif state.phase in TARGET_PHASES:
            legal_actions = self._target_actions(state)
        else:
            raise SCKError(f"unsupported SecretMafia phase: {state.phase}")

        return StrategicObservation(
            actor_id=str(state.actor_id),
            game_id=self.game_id,
            scene_id=f"day-{state.day_number}:{state.phase}",
            round_no=int(state.discussion_round_index or 1),
            phase=state.phase,
            visible_public_state={
                "day_number": state.day_number,
                "alive_players": list(map(int, state.alive_players)),
                "public_messages": [dict(x) for x in state.public_messages],
            },
            visible_private_state={
                "role": state.actor_role,
                "known_mafia": list(map(int, state.known_mafia)),
                "investigations": dict(state.investigations or {}),
                "private_messages": [dict(x) for x in state.private_messages],
                "pending_elimination": state.pending_elimination,
            },
            legal_actions=legal_actions,
            game_local_role=state.actor_role,
            game_local_stake={"survive": True, "faction_win": True},
            observation_history=tuple(state.public_messages) + tuple(state.private_messages),
        )

    @staticmethod
    def decision_to_textarena_action(
        decision: StrategicDecision,
        *,
        rendered_utterance: str | None = None,
    ) -> str:
        kind = str(decision.action.get("kind", ""))
        if kind in {"vote", "protect", "investigate", "mafia_eliminate"}:
            action = decision.action.get("textarena_action")
            if not action:
                raise SCKError("structured SecretMafia target action lacks textarena_action")
            return str(action)
        if kind == "communicate":
            if rendered_utterance is None:
                raise SCKError(
                    "discussion decision requires a separate language renderer; "
                    "SCK does not turn strategy directly into dialogue"
                )
            return rendered_utterance
        raise SCKError(f"cannot render unsupported decision kind: {kind}")


def default_public_communication_intent(actor_id: int) -> CommunicationIntent:
    return CommunicationIntent(
        channel="public_discussion",
        audience=("all_alive_players",),
        speech_act="state_position_and_request_evidence",
        disclosure_level="bounded",
        tone_constraints=("concise", "do_not_claim_hidden_truth"),
        floor_bid=0.5,
    )
