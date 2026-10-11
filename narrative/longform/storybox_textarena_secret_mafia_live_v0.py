"""Live TextArena SecretMafia runner for the StoryBox Strategic Cognition Kernel.

Purpose
-------
Run real :mod:`textarena` SecretMafia episodes so SCK variants can be compared on
an external benchmark instead of on prose quality.  This module is the bridge: it
converts *actor-visible* TextArena observations into
:class:`~narrative.longform.storybox_sck_v0.StrategicObservation` and consumes only
the structured action formats the environment accepts.

Information boundary (hard)
---------------------------
* The runner builds :class:`ActorView` objects from an explicit whitelist of
  environment fields: the actor's own observation inbox, ``alive_players``,
  ``phase`` and ``day_number``.  It never reads ``player_roles`` /
  ``secret_roles`` while a decision is being made.
* The actor's own role and Mafia teammates are recovered by parsing the private
  ``PROMPT`` observation the environment already delivered to that actor.
* Backstage truth (real roles, rewards, the Mafia's pending night target) is read
  only in :func:`evaluate_episode`, after every decision has been recorded.
* Policies receive frozen, tuple-only :class:`ActorView` objects; they never
  receive the environment or its ``state``.

Observed environment behaviour this design depends on (verified against
textarena 0.7.4; the probes that established it are kept at
``output/sck-evidence/probe_live_env.py`` and ``output/sck-evidence/probe_native_vote.py``)
----------------------------------------------------------------------
* ``textarena.core.State.add_observation`` strips every ``[Player N]`` role tag
  from ``PLAYER_ACTION`` messages.  The environment's own phase prompts ask for
  the ``[X]`` form and ``VoteHandler`` accepts both, so **this runner submits
  ``[N]``**, whose target survives the ordinary public observation stream
  unchanged.  ``action_format="player_tag"`` reproduces the broken behaviour and
  exists only so the difference can be tested.  With ``[N]`` a day vote cast
  before an actor's turn is visible to that actor, which is what
  ``broadcast_to_all=True`` in ``SecretMafiaEnv._record_vote`` intends; with
  ``[Player N]`` it arrives as the empty string and is lost.
* Observable evidence events: ``"Player X was killed during the night."``,
  ``"No one was killed tonight."``, ``"Player X was eliminated by vote."``, the
  Detective's private ``"Player X IS [NOT] a Mafia member."``, and public day
  votes with their targets intact.
* ``day_number`` is never incremented by the environment, so the runner keeps its
  own night counter.
* The environment resolves ties with the global ``random`` module and
  ``SecretMafiaEnv.reset`` seeds it.  Policies therefore use their own
  ``random.Random`` instance, so no policy can perturb environment randomness.

Deliberately unavailable in v0 (reported as unavailable, never faked)
---------------------------------------------------------------------
* ``persuasion_delta`` -- the template discussion renderer has no measurable
  persuasive effect on the other policies.
* learned evidence likelihoods -- :class:`BehaviorEvidenceModel` is an explicit
  hand-specified model awaiting replay calibration, and round 5 showed its
  hand-specified direction is wrong for play.
* LLM strategy-candidate generation and natural-language rendering.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
import random
import re
from typing import Any, Callable, Mapping, Sequence

from .storybox_sck_v0 import (
    BeliefState,
    EvidenceRecord,
    OpponentModel,
    SCKError,
    StrategicCognitionKernel,
    StrategicDecision,
    StrategicObservation,
)
from .storybox_sck_eval_v0 import (
    ActionCheckpoint,
    BeliefCheckpoint,
    CommunicationCheckpoint,
    EpisodeEvaluation,
    VariantConfig,
)
from .storybox_textarena_secret_mafia_adapter_v0 import (
    PHASE_DAY_DISCUSSION,
    PHASE_DAY_VOTING,
    PHASE_NIGHT_DETECTIVE,
    PHASE_NIGHT_DOCTOR,
    PHASE_NIGHT_MAFIA,
    SecretMafiaVisibleState,
    TARGET_PHASES,
    TextArenaSecretMafiaAdapter,
    evidence_from_known_alignment,
    initial_mafia_world_belief,
    mafia_world_id,
    marginal_mafia_probabilities,
    parse_mafia_world,
)

GAME_ID = -1

#: Day votes and night targets are submitted as ``[N]``, which is the format the
#: environment itself advertises in its phase prompts ("submit one vote in format
#: [X]", "Valid targets: [0], [3]").  ``State.add_observation`` strips every
#: ``[Player N]`` role tag from ``PLAYER_ACTION`` messages but leaves ``[N]``
#: alone, so the native form is the only encoding whose target survives the
#: ordinary public observation stream.  ``"player_tag"`` is kept so the
#: difference can be tested and demonstrated, never as the default.
TARGET_ACTION_FORMATS = ("native", "player_tag")
DEFAULT_TARGET_ACTION_FORMAT = "native"

#: Environment fields the runner may read while building a decision view.
#: Everything else in ``state`` is backstage truth.
DECISION_TIME_STATE_KEYS = ("phase", "day_number", "alive_players")

#: Attribute names that must never appear on an object handed to a policy.
FORBIDDEN_VIEW_ATTRIBUTES = (
    "player_roles",
    "secret_roles",
    "roles",
    "pending_elimination",
    "rewards",
    "game_info",
)

ACTION_KIND_BY_PHASE = {
    PHASE_NIGHT_MAFIA: "mafia_eliminate",
    PHASE_NIGHT_DOCTOR: "protect",
    PHASE_NIGHT_DETECTIVE: "investigate",
    PHASE_DAY_VOTING: "vote",
}

ROLE_RE = re.compile(r"Your role:\s*([A-Za-z]+)")
TEAMMATES_RE = re.compile(r"Your teammates are:\s*([^\n.]*)")
INVESTIGATION_RE = re.compile(
    r"Player\s+(\d+)\s+IS(\s+NOT\s+)?a Mafia member", re.IGNORECASE
)
NIGHT_KILL_RE = re.compile(r"Player\s+(\d+)\s+was killed during the night", re.IGNORECASE)
NIGHT_NONE_RE = re.compile(r"No one was killed tonight", re.IGNORECASE)
VOTE_ELIMINATION_RE = re.compile(r"Player\s+(\d+)\s+was eliminated by vote", re.IGNORECASE)
PLAYER_NUMBER_RE = re.compile(r"(\d+)")
#: Mirrors ``SecretMafiaEnv.voting_pattern``.
VOTE_TAG_RE = re.compile(r"\[(?:player\s*)?(\d+)\]", re.IGNORECASE)


def load_textarena_secret_mafia_env():
    """Import the live TextArena environment lazily.

    The SCK core, the adapter and this module stay importable without
    ``textarena`` so the offline test-suite can still run; only live play needs
    the dependency.
    """
    try:
        from textarena.envs.SecretMafia.env import SecretMafiaEnv  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - depends on environment
        raise SCKError(
            "textarena is not importable in this interpreter; live SecretMafia "
            "play is unavailable. Install textarena to run the live A/B."
        ) from exc
    return SecretMafiaEnv


def secret_mafia_role_count(num_players: int, mafia_ratio: float = 0.25) -> int:
    """Public game rule, mirroring ``SecretMafiaEnv._assign_roles``.

    The number of Mafia is a published rule parameter derived from the player
    count, not per-player backstage truth.
    """
    if num_players < 1:
        raise SCKError("num_players must be positive")
    return max(1, round(num_players * mafia_ratio))


def textarena_target_action(
    target: int, action_format: str = DEFAULT_TARGET_ACTION_FORMAT
) -> str:
    if action_format not in TARGET_ACTION_FORMATS:
        raise SCKError(f"unknown target action format: {action_format}")
    if action_format == "player_tag":
        return f"[Player {int(target)}]"
    return f"[{int(target)}]"


# ---------------------------------------------------------------------------
# Actor-visible view
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptEntry:
    """One observation as delivered to one actor, with when it was delivered."""

    from_id: int
    message: str
    observation_type: str
    phase: str
    night_number: int
    public: bool

    @property
    def speaker(self) -> int | None:
        return None if self.from_id == GAME_ID else self.from_id


@dataclass(frozen=True)
class ActorView:
    """Everything one actor may legitimately know at its turn.

    Frozen and tuple-only, so a policy cannot mutate it and cannot reach the
    environment through it.
    """

    actor_id: int
    num_players: int
    mafia_count: int
    role: str
    mafia_teammates: tuple[int, ...]
    phase: str
    night_number: int
    alive_players: tuple[int, ...]
    legal_targets: tuple[int, ...]
    discussion_turn: int
    pending: tuple[TranscriptEntry, ...]
    history: tuple[TranscriptEntry, ...]
    own_actions: tuple[tuple[str, int | None], ...]
    investigations: tuple[tuple[int, bool], ...]
    #: Day votes already cast by other seats in the current voting round, in
    #: submission order.  Empty unless the runner runs the explicitly labelled
    #: reconstructed-channel arm, because the environment destroys vote targets
    #: before broadcasting them (see the module docstring).  A player could
    #: always observe votes cast before its own turn; the reconstruction only
    #: restores the target the environment intended to broadcast.
    public_vote_record: tuple[tuple[int, int], ...] = ()
    #: Names of channels on this view whose content was reconstructed by the
    #: runner rather than delivered by the environment.  Exposing reconstructed
    #: content without declaring it here is an information-boundary violation.
    reconstructed_channels: tuple[str, ...] = ()

    @property
    def is_mafia(self) -> bool:
        return self.role.lower() == "mafia"

    def public_history(self) -> tuple[TranscriptEntry, ...]:
        return tuple(row for row in self.history if row.public)

    def as_visible_state(
        self, adapter: TextArenaSecretMafiaAdapter
    ) -> SecretMafiaVisibleState:
        """Project the view onto the adapter's information-safe input type."""
        return SecretMafiaVisibleState(
            actor_id=self.actor_id,
            num_players=self.num_players,
            phase=self.phase,
            day_number=self.night_number,
            alive_players=list(self.alive_players),
            actor_role=self.role,
            public_messages=[
                {"from": row.from_id, "message": row.message, "type": row.observation_type}
                for row in self.history
                if row.public
            ],
            private_messages=[
                {"from": row.from_id, "message": row.message, "type": row.observation_type}
                for row in self.history
                if not row.public
            ],
            known_mafia=list(self.mafia_teammates),
            investigations=dict(self.investigations),
            # Never populated: the Mafia's pending night target is backstage.
            pending_elimination=None,
            discussion_round_index=self.discussion_turn,
        )


RECONSTRUCTED_VOTE_CHANNEL = "public_day_vote"


def assert_information_safe(view: ActorView) -> None:
    """Fail loudly if a decision view ever exposes backstage state."""
    for name in FORBIDDEN_VIEW_ATTRIBUTES:
        if hasattr(view, name):
            raise SCKError(f"actor view leaks backstage attribute: {name}")
    state = view.as_visible_state(TextArenaSecretMafiaAdapter())
    if state.pending_elimination is not None:
        raise SCKError("actor view leaks the pending night elimination")
    undeclared = set(view.reconstructed_channels) - {RECONSTRUCTED_VOTE_CHANNEL}
    if undeclared:
        raise SCKError(f"actor view declares an unknown reconstructed channel: {sorted(undeclared)}")
    if view.public_vote_record and RECONSTRUCTED_VOTE_CHANNEL not in view.reconstructed_channels:
        raise SCKError(
            "actor view carries a reconstructed vote record without declaring "
            f"{RECONSTRUCTED_VOTE_CHANNEL!r}"
        )


def parse_role_and_teammates(prompt_text: str) -> tuple[str, tuple[int, ...]]:
    role_match = ROLE_RE.search(prompt_text)
    if not role_match:
        raise SCKError("actor prompt does not state a role")
    role = role_match.group(1)
    teammates: tuple[int, ...] = ()
    teammates_match = TEAMMATES_RE.search(prompt_text)
    if teammates_match:
        teammates = tuple(
            int(x) for x in PLAYER_NUMBER_RE.findall(teammates_match.group(1))
        )
    if role.lower() == "mafia" and not teammates:
        raise SCKError("mafia prompt does not state teammates")
    return role, teammates


def parse_investigations(
    history: Sequence[TranscriptEntry],
) -> tuple[tuple[int, bool], ...]:
    out: list[tuple[int, bool]] = []
    for row in history:
        if row.observation_type != "GAME_MESSAGE":
            continue
        match = INVESTIGATION_RE.search(row.message)
        if match:
            out.append((int(match.group(1)), match.group(2) is None))
    return tuple(out)


def legal_targets_for(
    *,
    role: str,
    phase: str,
    alive_players: Sequence[int],
    mafia_teammates: Sequence[int],
    actor_id: int,
) -> tuple[int, ...]:
    """Legal target set, derived the same way as the existing adapter."""
    if phase == PHASE_NIGHT_MAFIA:
        if role.lower() != "mafia":
            return ()
        blocked = set(mafia_teammates) | {actor_id}
        return tuple(p for p in alive_players if p not in blocked)
    if phase in (PHASE_NIGHT_DOCTOR, PHASE_NIGHT_DETECTIVE, PHASE_DAY_VOTING):
        return tuple(p for p in alive_players if p != actor_id)
    return ()


def parse_vote_target(message: str) -> int | None:
    match = VOTE_TAG_RE.search(message)
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Evidence model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BehaviorEvidenceModel:
    """Explicit, hand-specified evidence likelihoods for SecretMafia.

    These are *not* learned and *not* calibrated against replay yet.  They are
    written down so they are auditable and so a later replay calibration can
    replace them.  The adapter never invents these numbers itself.

    Rationale for each live term:

    ``night_kill_mafia_likelihood``
        Mafia choose whom to eliminate; killing one of their own is close to
        self-defeating, so a night victim is very unlikely to be Mafia.
    ``doctor_saved_target_likelihood``
        When nobody dies at night and the Doctor protected ``Y``, the only
        mechanism producing that outcome is the Mafia targeting ``Y``.  This
        combines the Doctor's own action with a public outcome and is a
        legitimate private inference, not truth access.

    ``mafia_votes_*``
        Structural property of the game: Mafia avoid eliminating their own
        team, so a vote by a suspected Mafia for ``t`` lowers ``t``'s Mafia
        probability.  With ``action_format="native"`` this term is live, because
        day-vote targets survive the observation stream.
    """

    night_kill_mafia_likelihood: float = 0.02
    night_kill_reliability: float = 0.95
    doctor_saved_target_likelihood: float = 0.05
    doctor_saved_reliability: float = 0.90
    mafia_votes_teammate_likelihood: float = 0.05
    mafia_votes_non_teammate_likelihood: float = 0.95
    vote_evidence_reliability: float = 0.80


def night_kill_evidence(
    *,
    evidence_id: str,
    victim: int,
    belief: BeliefState,
    model: BehaviorEvidenceModel,
) -> EvidenceRecord:
    """A night victim is very unlikely to be Mafia."""
    ratios = {
        world_id: (
            model.night_kill_mafia_likelihood
            if victim in parse_mafia_world(world_id)
            else 1.0
        )
        for world_id in belief.hypotheses
    }
    return EvidenceRecord(
        evidence_id=evidence_id,
        source="public_night_kill",
        likelihood_ratio_by_hypothesis=ratios,
        reliability=model.night_kill_reliability,
        informative=True,
        description=f"Player {victim} was killed during the night",
    )


def doctor_saved_evidence(
    *,
    evidence_id: str,
    protected: int,
    belief: BeliefState,
    model: BehaviorEvidenceModel,
) -> EvidenceRecord:
    """A failed night kill implies the Mafia targeted the protected player."""
    ratios = {
        world_id: (
            model.doctor_saved_target_likelihood
            if protected in parse_mafia_world(world_id)
            else 1.0
        )
        for world_id in belief.hypotheses
    }
    return EvidenceRecord(
        evidence_id=evidence_id,
        source="private_doctor_save",
        likelihood_ratio_by_hypothesis=ratios,
        reliability=model.doctor_saved_reliability,
        informative=True,
        description=(
            f"No one died at night while Player {protected} was protected; "
            "the Mafia most likely targeted that player"
        ),
    )


def recorded_vote_evidence(
    *,
    evidence_id: str,
    voter: int,
    target: int,
    belief: BeliefState,
    model: BehaviorEvidenceModel,
) -> EvidenceRecord:
    """Evidence from an observed vote.

    Used by the native channel (a day vote whose target survived the public
    observation stream) and by the reconstructed sensitivity arm.  Never used
    for a vote the actor could not have observed.
    """
    ratios: dict[str, float] = {}
    for world_id in belief.hypotheses:
        world = parse_mafia_world(world_id)
        if voter in world:
            ratios[world_id] = (
                model.mafia_votes_teammate_likelihood
                if target in world
                else model.mafia_votes_non_teammate_likelihood
            )
        else:
            ratios[world_id] = 1.0
    return EvidenceRecord(
        evidence_id=evidence_id,
        source="recorded_vote",
        likelihood_ratio_by_hypothesis=ratios,
        reliability=model.vote_evidence_reliability,
        informative=True,
        description=f"Player {voter} voted for Player {target}",
    )


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@dataclass
class DecisionRecord:
    step_id: str
    actor_id: int
    phase: str
    chosen_action_id: str | None
    target: int | None
    action_string: str
    legal_targets: tuple[int, ...] = ()
    belief: BeliefState | None = None
    decision: StrategicDecision | None = None
    utterance: str | None = None
    protected_facts: tuple[str, ...] = ()
    disclosed_facts: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def render_discussion(view: ActorView, target: int | None) -> str:
    """Template language renderer.

    It may describe a position but never changes the chosen strategic action.
    It deliberately avoids the ``[Player N]`` vote syntax, so a rendered
    utterance can never be parsed as a vote.
    """
    if target is None:
        return f"Day {view.night_number}: nothing material to add."
    return f"Day {view.night_number}: I am watching Player {target}."


class SecretMafiaPolicy:
    """Base policy: no memory, no belief, uniform random legal target."""

    variant_id = "plain"

    #: Informed policies break ties by lowest player id instead of drawing from
    #: their RNG.  Otherwise ``belief`` and ``belief_planning`` consume different
    #: numbers of random values on different phases and diverge in arbitrary
    #: tie-breaks, which contaminates the planner ablation.  ``"random"``
    #: restores the stochastic tie-break for sensitivity checks.
    tie_break = "lowest_id"

    def __init__(
        self,
        *,
        num_players: int,
        seed: int,
        model: BehaviorEvidenceModel | None = None,
        tie_break: str | None = None,
        action_format: str = DEFAULT_TARGET_ACTION_FORMAT,
    ):
        self.num_players = num_players
        self.model = model or BehaviorEvidenceModel()
        if tie_break is not None:
            if tie_break not in {"lowest_id", "random"}:
                raise SCKError(f"unknown tie_break mode: {tie_break}")
            self.tie_break = tie_break
        if action_format not in TARGET_ACTION_FORMATS:
            raise SCKError(f"unknown target action format: {action_format}")
        self.action_format = action_format
        # Own RNG: the environment seeds the global ``random`` module, so using
        # the global generator here would perturb environment randomness.
        self.rng = random.Random(seed)
        self.adapter = TextArenaSecretMafiaAdapter()
        self.uses_memory = False
        self.uses_belief = False

    # -- helpers ---------------------------------------------------------
    def _best_target(
        self, candidates: Sequence[int], key, *, maximise: bool
    ) -> int:
        """Pick the extremal candidate, resolving ties deterministically."""
        values = {target: key(target) for target in candidates}
        best = (max if maximise else min)(values.values())
        tied = sorted(
            target
            for target, value in values.items()
            if math.isclose(value, best, rel_tol=1e-12, abs_tol=1e-15)
        )
        if self.tie_break == "random":
            return self.rng.choice(tied)
        return tied[0]

    def _argmax(self, candidates: Sequence[int], key) -> int:
        return self._best_target(candidates, key, maximise=True)

    def _argmin(self, candidates: Sequence[int], key) -> int:
        return self._best_target(candidates, key, maximise=False)

    def _pick_random(self, view: ActorView) -> int | None:
        if not view.legal_targets:
            return None
        return self.rng.choice(list(view.legal_targets))

    def protected_facts(self, view: ActorView) -> tuple[str, ...]:
        facts = [f"role:{view.role}"]
        if view.is_mafia:
            facts.append(
                "mafia_team:" + ",".join(str(x) for x in view.mafia_teammates)
            )
        for player, is_mafia in view.investigations:
            facts.append(
                f"investigation:{player}={'mafia' if is_mafia else 'village'}"
            )
        return tuple(facts)

    def own_action_target(self, view: ActorView, kind: str) -> int | None:
        for action_id, target in reversed(view.own_actions):
            if action_id.startswith(kind + ":"):
                return target
        return None

    # -- protocol --------------------------------------------------------
    def act(self, view: ActorView) -> DecisionRecord:
        assert_information_safe(view)
        step_id = (
            f"p{view.actor_id}-n{view.night_number}-{view.phase}-{view.discussion_turn}"
        )
        if view.phase == PHASE_DAY_DISCUSSION:
            utterance = render_discussion(view, None)
            return DecisionRecord(
                step_id=step_id,
                actor_id=view.actor_id,
                phase=view.phase,
                chosen_action_id="communicate:public",
                target=None,
                action_string=utterance,
                utterance=utterance,
                protected_facts=self.protected_facts(view),
            )
        target = self.choose_target(view)
        if target is None:
            raise SCKError(f"no legal target available in phase {view.phase}")
        kind = ACTION_KIND_BY_PHASE[view.phase]
        return DecisionRecord(
            step_id=step_id,
            actor_id=view.actor_id,
            phase=view.phase,
            chosen_action_id=f"{kind}:{target}",
            target=target,
            action_string=textarena_target_action(target, self.action_format),
            legal_targets=view.legal_targets,
            protected_facts=self.protected_facts(view),
        )

    def choose_target(self, view: ActorView) -> int | None:
        return self._pick_random(view)


class PlainPolicy(SecretMafiaPolicy):
    """No memory, no belief: uniform random legal target."""

    variant_id = "plain"


class MemoryPolicy(SecretMafiaPolicy):
    """Transcript memory without probabilistic belief.

    Uses only hard, non-probabilistic facts it can remember: a Detective's own
    confirmed results.  Otherwise it stays uninformed and picks uniformly at
    random.  (A Mafia's legal target set already excludes its teammates, so no
    extra rule is needed there.)
    """

    variant_id = "memory"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.uses_memory = True

    def choose_target(self, view: ActorView) -> int | None:
        legal = list(view.legal_targets)
        if not legal:
            return None
        confirmed_mafia = {p for p, is_mafia in view.investigations if is_mafia}
        watched = [p for p in legal if p in confirmed_mafia]
        if watched:
            return self.rng.choice(watched)
        return self.rng.choice(legal)


class BeliefPolicy(SecretMafiaPolicy):
    """Auditable hidden-world belief plus marginal-probability target choice."""

    variant_id = "belief"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.uses_memory = True
        self.uses_belief = True
        self.beliefs: dict[int, BeliefState] = {}
        self.processed: dict[int, int] = {}
        self.vote_cursor: dict[int, int] = {}

    # -- belief maintenance ---------------------------------------------
    def belief_for(self, view: ActorView) -> BeliefState:
        belief = self.beliefs.get(view.actor_id)
        if belief is None:
            belief = initial_mafia_world_belief(
                num_players=view.num_players,
                actor_id=view.actor_id,
                actor_role=view.role,
                mafia_count=view.mafia_count,
                known_mafia=view.mafia_teammates,
            )
            self.beliefs[view.actor_id] = belief
            self.processed[view.actor_id] = 0
        self.update_belief(view, belief)
        return belief

    def update_belief(self, view: ActorView, belief: BeliefState) -> None:
        """Apply evidence from each actor observation exactly once."""
        history = view.history
        start = self.processed.get(view.actor_id, 0)
        for index in range(start, len(history)):
            row = history[index]
            if row.observation_type == "PLAYER_ACTION":
                self._apply_native_vote_evidence(view, row, index, belief)
                continue
            if row.observation_type != "GAME_MESSAGE":
                continue
            kill = NIGHT_KILL_RE.search(row.message)
            if kill:
                belief.update(
                    night_kill_evidence(
                        evidence_id=f"p{view.actor_id}-kill-{index}",
                        victim=int(kill.group(1)),
                        belief=belief,
                        model=self.model,
                    )
                )
                continue
            if NIGHT_NONE_RE.search(row.message):
                protected = self.own_action_target(view, "protect")
                if protected is not None:
                    belief.update(
                        doctor_saved_evidence(
                            evidence_id=f"p{view.actor_id}-save-{index}",
                            protected=protected,
                            belief=belief,
                            model=self.model,
                        )
                    )
                continue
            investigation = INVESTIGATION_RE.search(row.message)
            if investigation and not row.public:
                target = int(investigation.group(1))
                belief.update(
                    evidence_from_known_alignment(
                        evidence_id=f"p{view.actor_id}-investigate-{index}",
                        source="detective_private_result",
                        target_player=target,
                        is_mafia=investigation.group(2) is None,
                        current_belief=belief,
                        reliability=1.0,
                        description=f"Detective result for Player {target}",
                    )
                )
        self.processed[view.actor_id] = len(history)
        self._update_from_vote_record(view, belief)

    def _apply_native_vote_evidence(
        self,
        view: ActorView,
        row: TranscriptEntry,
        index: int,
        belief: BeliefState,
    ) -> None:
        """Native channel: a day vote whose target survived the observation stream.

        Only day-voting player actions are used.  The Mafia's night votes share
        the same message shape but are tagged with a night phase, so they are
        excluded here to avoid double counting with the night-kill evidence.
        """
        if row.phase != PHASE_DAY_VOTING or row.speaker is None:
            return
        target = parse_vote_target(row.message)
        if target is None or row.speaker == view.actor_id:
            return
        belief.update(
            recorded_vote_evidence(
                evidence_id=f"p{view.actor_id}-n{row.night_number}-nativevote-{row.speaker}-{target}-{index}",
                voter=row.speaker,
                target=target,
                belief=belief,
                model=self.model,
            )
        )

    def _update_from_vote_record(self, view: ActorView, belief: BeliefState) -> None:
        """Apply evidence from the reconstructed public day-vote record.

        ``recorded_vote_evidence`` was written for replay inputs; in live play it
        stays dead code unless the runner runs the labelled reconstructed-channel
        arm, because the environment destroys vote targets.
        """
        record = view.public_vote_record
        if not record:
            return
        cursor = self.vote_cursor.get(view.actor_id, 0)
        if cursor > len(record):
            # A new voting round started and the record was reset.
            cursor = 0
        for index in range(cursor, len(record)):
            voter, target = record[index]
            if voter == view.actor_id:
                continue
            belief.update(
                recorded_vote_evidence(
                    evidence_id=f"p{view.actor_id}-n{view.night_number}-vote-{voter}-{target}",
                    voter=voter,
                    target=target,
                    belief=belief,
                    model=self.model,
                )
            )
        self.vote_cursor[view.actor_id] = len(record)

    # -- target choice ---------------------------------------------------
    @staticmethod
    def _binary_entropy(p: float) -> float:
        p = min(max(p, 1e-9), 1 - 1e-9)
        return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

    def _detective_pick(self, view: ActorView, marginals: Mapping[int, float]) -> int:
        """Maximise expected alignment information; skip already-known players."""
        known = {player for player, _ in view.investigations}
        candidates = [t for t in view.legal_targets if t not in known]
        if not candidates:
            candidates = list(view.legal_targets)
        return self._argmax(
            candidates, lambda t: self._binary_entropy(marginals[t])
        )

    def choose_target(self, view: ActorView) -> int | None:
        legal = list(view.legal_targets)
        if not legal:
            return None
        belief = self.belief_for(view)
        marginals = marginal_mafia_probabilities(belief, view.num_players)
        role = view.role.lower()
        if role == "detective":
            return self._detective_pick(view, marginals)
        if role in {"doctor", "mafia"}:
            # Both want to remove a player who is unlikely to be Mafia: the Mafia
            # eliminates a villager, the Doctor protects the Mafia's likely victim.
            return self._argmin(legal, lambda t: marginals[t])
        return self._argmax(legal, lambda t: marginals[t])

    def act(self, view: ActorView) -> DecisionRecord:
        record = super().act(view)
        belief = self.beliefs.get(view.actor_id)
        if belief is not None and view.phase in TARGET_PHASES:
            # Attached for evaluation only; the policy already used it in
            # ``choose_target``.  ``evaluate_episode`` snapshots it so later
            # updates cannot rewrite an earlier checkpoint.
            record.belief = belief
        return record


class BeliefPlanningPolicy(BeliefPolicy):
    """Belief policy plus two-ply collision planning on contested phases.

    Only the Mafia night kill and the day vote involve action collision.  The
    Doctor and Detective phases have no opponent response to plan against, so the
    policy falls back to the belief policy there instead of inventing a fake
    two-ply model.
    """

    variant_id = "belief_planning"

    def __init__(self, risk_aversion: float = 0.15, **kwargs):
        super().__init__(**kwargs)
        self.kernel = StrategicCognitionKernel(risk_aversion=risk_aversion)
        self.opponents: dict[int, dict[int, OpponentModel]] = {}
        self.last_decision: StrategicDecision | None = None

    def opponents_for(self, view: ActorView) -> dict[int, OpponentModel]:
        models = self.opponents.setdefault(view.actor_id, {})
        for pid in view.alive_players:
            if pid != view.actor_id:
                models.setdefault(pid, OpponentModel(str(pid)))
        return models

    @staticmethod
    def _faction_utility(
        world: frozenset[int], alive: Sequence[int], removed: int, role: str
    ) -> float:
        remaining = [p for p in alive if p != removed]
        mafia_alive = sum(1 for p in remaining if p in world)
        village_alive = len(remaining) - mafia_alive
        if mafia_alive == 0:
            value = 1.0
        elif mafia_alive >= village_alive:
            value = -1.0
        else:
            value = (village_alive - mafia_alive) / (village_alive + mafia_alive)
        return -value if role.lower() == "mafia" else value

    def _rollout(self, role: str) -> Callable[..., float]:
        def rollout(observation, action, hypothesis, opponent_id, response_id):
            target = action.get("target")
            if target is None:
                return 0.0
            target = int(target)
            world = parse_mafia_world(hypothesis)
            alive = [int(p) for p in observation.visible_public_state["alive_players"]]
            if response_id is None:
                # Documented, deliberately crude collision model.
                same_target_probability = 0.5
            else:
                response_target = int(str(response_id).split(":")[-1])
                same_target_probability = 0.75 if response_target == target else 0.35
            killed_target = self._faction_utility(world, alive, target, role)
            others = [p for p in alive if p != target]
            if others:
                other = sum(
                    self._faction_utility(world, alive, p, role) for p in others
                ) / len(others)
            else:
                other = killed_target
            return (
                same_target_probability * killed_target
                + (1.0 - same_target_probability) * other
            )

        return rollout

    def choose_target(self, view: ActorView) -> int | None:
        if view.phase not in (PHASE_DAY_VOTING, PHASE_NIGHT_MAFIA):
            return super().choose_target(view)
        legal = list(view.legal_targets)
        if not legal:
            return None
        belief = self.belief_for(view)
        visible = view.as_visible_state(self.adapter)
        observation = self.adapter.to_strategic_observation(visible)
        responses = [
            f"vote:{t}" for t in view.alive_players if t != view.actor_id
        ]
        opponent_ids = [str(p) for p in view.alive_players if p != view.actor_id]
        rows = []
        for row in observation.legal_actions:
            augmented = dict(row)
            augmented["opponent_legal_actions"] = {
                pid: list(responses) for pid in opponent_ids
            }
            rows.append(augmented)
        observation = replace(observation, legal_actions=tuple(rows))
        decision = self.kernel.decide(
            observation,
            belief,
            self.opponents_for(view),
            self._rollout(view.role),
            protected_information=self.protected_facts(view),
        )
        self.last_decision = decision
        return int(decision.action["target"])

    def act(self, view: ActorView) -> DecisionRecord:
        self.last_decision = None
        record = super().act(view)
        if self.last_decision is not None:
            record.decision = self.last_decision
        return record


POLICY_BY_VARIANT: dict[str, type[SecretMafiaPolicy]] = {
    "plain": PlainPolicy,
    "memory": MemoryPolicy,
    "belief": BeliefPolicy,
    "belief_planning": BeliefPlanningPolicy,
}


def build_policy(
    variant: VariantConfig,
    *,
    num_players: int,
    seed: int,
    tie_break: str | None = None,
    action_format: str = DEFAULT_TARGET_ACTION_FORMAT,
    policy_classes: Mapping[str, type[SecretMafiaPolicy]] | None = None,
) -> SecretMafiaPolicy:
    registry = policy_classes or POLICY_BY_VARIANT
    try:
        policy_type = registry[variant.variant_id]
    except KeyError as exc:
        raise SCKError(f"unknown SCK variant: {variant.variant_id}") from exc
    return policy_type(
        num_players=num_players,
        seed=seed,
        tie_break=tie_break,
        action_format=action_format,
    )


# ---------------------------------------------------------------------------
# Live runner
# ---------------------------------------------------------------------------


@dataclass
class EpisodeTrace:
    steps: int = 0
    decisions: list[DecisionRecord] = field(default_factory=list)
    invalid_moves: int = 0
    termination_reason: str = ""
    nights_played: int = 0
    empty_player_action_messages: int = 0
    vote_eliminations: int = 0
    night_kills: int = 0
    #: Channels the runner reconstructed instead of receiving from the
    #: environment, recorded so every artifact is self-describing.
    reconstructed_channels: tuple[str, ...] = ()
    #: Evaluation-only snapshot: the Mafia's pending target at decision time.
    #: It is read by the runner *after* a decision has been produced, stored on
    #: this trace, and consumed by :func:`oracle_action_values`.  It is never
    #: placed on an :class:`ActorView`, so no policy can observe it.
    evaluation_only_pending_elimination_by_step: dict[str, int | None] = field(
        default_factory=dict
    )


def secret_mafia_role_schedule(
    *,
    num_players: int,
    seed: int,
    mafia_ratio: float = 0.25,
    discussion_rounds: int = 3,
    env_factory: Callable[..., Any] | None = None,
) -> dict[int, str]:
    """Read a seed's role schedule without playing a game.

    This is experimenter-side truth used only to decide **which policy sits on
    which seat** in a cross-play condition, the way any A/B designer assigns
    arms.  It never reaches a policy: a policy still receives only its own
    :class:`ActorView`, so the information boundary is unchanged.  The schedule
    is a deterministic function of the seed, so the throwaway reset below
    reproduces exactly the roles the real episode will get.
    """
    factory = env_factory or load_textarena_secret_mafia_env()
    env = factory(mafia_ratio=mafia_ratio, discussion_rounds=discussion_rounds)
    env.reset(num_players=num_players, seed=seed)
    return {pid: str(env.player_roles[pid]) for pid in range(num_players)}


class SecretMafiaLiveRunner:
    """Drive a live TextArena SecretMafia game with SCK policies.

    Every seat is controlled by the same variant, so an episode is SCK
    self-play.  Truth is read only after the episode ends.
    """

    def __init__(
        self,
        *,
        mafia_ratio: float = 0.25,
        discussion_rounds: int = 3,
        max_steps: int = 2000,
        evidence_model: BehaviorEvidenceModel | None = None,
        tie_break: str = "lowest_id",
        action_format: str = DEFAULT_TARGET_ACTION_FORMAT,
        policy_classes: Mapping[str, type[SecretMafiaPolicy]] | None = None,
        public_vote_record: bool = False,
        env_factory: Callable[..., Any] | None = None,
    ):
        self.mafia_ratio = mafia_ratio
        self.discussion_rounds = discussion_rounds
        self.max_steps = max_steps
        self.evidence_model = evidence_model or BehaviorEvidenceModel()
        self.tie_break = tie_break
        if action_format not in TARGET_ACTION_FORMATS:
            raise SCKError(f"unknown target action format: {action_format}")
        self.action_format = action_format
        if public_vote_record and action_format == "native":
            raise SCKError(
                "public_vote_record reconstructs the vote record that the native "
                "action format already makes observable; enabling both would "
                "double-count the same evidence"
            )
        #: Optional policy registry override, used by instrumentation such as
        #: the A/B harness's belief-discrimination diagnostic.
        self.policy_classes = policy_classes
        #: Off by default.  When on, the runner reconstructs the day-vote record
        #: the environment intends to broadcast but destroys, and marks every
        #: view that carries it.  Only meaningful with the legacy
        #: ``action_format="player_tag"``; it is a labelled sensitivity arm,
        #: never the primary measurement.
        self.public_vote_record = public_vote_record
        self._env_factory = env_factory

    def _make_env(self):
        factory = self._env_factory
        if factory is None:
            factory = load_textarena_secret_mafia_env()
        return factory(
            mafia_ratio=self.mafia_ratio, discussion_rounds=self.discussion_rounds
        )

    # -- transcript plumbing --------------------------------------------
    @staticmethod
    def _phase_name(raw: Any) -> str:
        return raw.value if hasattr(raw, "value") else str(raw)

    def _drain(
        self,
        state,
        transcript: dict[int, list[TranscriptEntry]],
        drained: dict[int, int],
        phase: str,
        night_number: int,
        trace: EpisodeTrace,
    ) -> None:
        new_by_player: dict[int, list[Any]] = {}
        for pid in range(state.num_players):
            inbox = state.observations[pid]
            new_by_player[pid] = list(inbox[drained[pid]:])
            drained[pid] = len(inbox)
        recipients: dict[tuple[int, str, str], set[int]] = {}
        for pid, rows in new_by_player.items():
            for row in rows:
                recipients.setdefault((row[0], row[1], row[2].name), set()).add(pid)
        for pid, rows in new_by_player.items():
            for row in rows:
                key = (row[0], row[1], row[2].name)
                if row[2].name == "PLAYER_ACTION" and row[1] == "":
                    trace.empty_player_action_messages += 1
                transcript[pid].append(
                    TranscriptEntry(
                        from_id=row[0],
                        message=row[1],
                        observation_type=row[2].name,
                        phase=phase,
                        night_number=night_number,
                        public=len(recipients[key]) == state.num_players,
                    )
                )

    # -- actor view ------------------------------------------------------
    @staticmethod
    def _prompt_text(history: Sequence[TranscriptEntry]) -> str:
        for row in history:
            if row.observation_type == "PROMPT":
                return row.message
        raise SCKError("actor has no PROMPT observation to recover its role from")

    def _build_view(
        self,
        *,
        state,
        transcript: dict[int, list[TranscriptEntry]],
        consumed: dict[int, int],
        own_actions: dict[int, list[tuple[str, int | None]]],
        discussion_turn: dict[int, int],
        actor_id: int,
        mafia_count: int,
        night_number: int,
        current_round_votes: Sequence[tuple[int, int]] = (),
    ) -> ActorView:
        history = tuple(transcript[actor_id])
        pending = history[consumed[actor_id]:]
        consumed[actor_id] = len(history)
        role, teammates = parse_role_and_teammates(self._prompt_text(history))
        phase = self._phase_name(state.game_state["phase"])
        alive = tuple(sorted(int(p) for p in state.game_state["alive_players"]))
        reconstruct = bool(self.public_vote_record) and phase == PHASE_DAY_VOTING
        return ActorView(
            actor_id=actor_id,
            num_players=int(state.num_players),
            mafia_count=mafia_count,
            role=role,
            mafia_teammates=teammates,
            phase=phase,
            night_number=night_number,
            alive_players=alive,
            legal_targets=legal_targets_for(
                role=role,
                phase=phase,
                alive_players=alive,
                mafia_teammates=teammates,
                actor_id=actor_id,
            ),
            discussion_turn=discussion_turn[actor_id],
            pending=pending,
            history=history,
            own_actions=tuple(own_actions[actor_id]),
            investigations=parse_investigations(history),
            public_vote_record=tuple(current_round_votes) if reconstruct else (),
            reconstructed_channels=(
                (RECONSTRUCTED_VOTE_CHANNEL,) if reconstruct else ()
            ),
        )

    # -- episode ---------------------------------------------------------
    def run_episode(
        self,
        *,
        variant: VariantConfig | None = None,
        seat_variants: Mapping[int, VariantConfig] | None = None,
        condition_id: str | None = None,
        num_players: int = 6,
        seed: int = 0,
    ) -> EpisodeEvaluation:
        """Play one episode.

        Either ``variant`` (one policy drives every seat) or ``seat_variants``
        (a policy per seat) must be given.  ``seat_variants`` is how cross-play
        seats an informed policy against a fixed baseline.  Which policy sits on
        which seat is experiment design, decided by the caller from the seed's
        role schedule; the policies themselves still only ever see their own
        :class:`ActorView`, so the information boundary is unaffected.
        """
        if seat_variants is None:
            if variant is None:
                raise SCKError("run_episode requires variant or seat_variants")
            seat_variants = {pid: variant for pid in range(num_players)}
        else:
            seat_variants = {int(k): v for k, v in seat_variants.items()}
            missing = set(range(num_players)) - set(seat_variants)
            if missing:
                raise SCKError(f"seat_variants is missing seats: {sorted(missing)}")
        label = condition_id or (
            variant.variant_id
            if variant is not None
            else "+".join(
                sorted({v.variant_id for v in seat_variants.values()})
            )
        )

        mafia_count = secret_mafia_role_count(num_players, self.mafia_ratio)
        env = self._make_env()
        env.reset(num_players=num_players, seed=seed)
        state = env.state
        policies = {
            pid: build_policy(
                seat_variants[pid],
                num_players=num_players,
                seed=seed * 1000 + pid,
                tie_break=self.tie_break,
                action_format=self.action_format,
                policy_classes=self.policy_classes,
            )
            for pid in range(num_players)
        }
        transcript: dict[int, list[TranscriptEntry]] = {
            pid: [] for pid in range(num_players)
        }
        drained = {pid: 0 for pid in range(num_players)}
        consumed = {pid: 0 for pid in range(num_players)}
        own_actions: dict[int, list[tuple[str, int | None]]] = {
            pid: [] for pid in range(num_players)
        }
        discussion_turn = {pid: 0 for pid in range(num_players)}
        current_round_votes: list[tuple[int, int]] = []
        trace = EpisodeTrace()
        night_number = 1

        self._drain(
            state,
            transcript,
            drained,
            self._phase_name(state.game_state["phase"]),
            night_number,
            trace,
        )

        while not state.done and trace.steps < self.max_steps:
            actor_id = int(state.current_player_id)
            phase_before = self._phase_name(state.game_state["phase"])
            view = self._build_view(
                state=state,
                transcript=transcript,
                consumed=consumed,
                own_actions=own_actions,
                discussion_turn=discussion_turn,
                actor_id=actor_id,
                mafia_count=mafia_count,
                night_number=night_number,
                current_round_votes=current_round_votes,
            )
            record = policies[actor_id].act(view)
            if (
                self.public_vote_record
                and phase_before == PHASE_DAY_VOTING
                and record.target is not None
            ):
                current_round_votes.append((actor_id, record.target))
            own_actions[actor_id].append((record.chosen_action_id or "", record.target))
            if phase_before == PHASE_DAY_DISCUSSION:
                discussion_turn[actor_id] += 1
            trace.decisions.append(record)
            # Evaluation-only snapshot taken after the decision exists; it never
            # reaches a policy (see EpisodeTrace field documentation).
            trace.evaluation_only_pending_elimination_by_step[record.step_id] = (
                state.game_state.get("pending_elimination")
            )
            turn_before = int(state.turn)
            env.step(record.action_string)
            trace.steps += 1
            if int(state.turn) == turn_before and not state.done:
                trace.invalid_moves += 1
            phase_after = self._phase_name(state.game_state["phase"])
            self._drain(
                state, transcript, drained, phase_after, night_number, trace
            )
            if phase_before == PHASE_DAY_VOTING and phase_after == PHASE_NIGHT_MAFIA:
                night_number += 1
                discussion_turn = {pid: 0 for pid in range(num_players)}
                current_round_votes = []
                trace.nights_played += 1

        if not state.done:
            raise SCKError(
                f"episode exceeded max_steps={self.max_steps} without terminating"
            )
        trace.reconstructed_channels = (
            (RECONSTRUCTED_VOTE_CHANNEL,) if self.public_vote_record else ()
        )

        for row in state.logs:
            if NIGHT_KILL_RE.search(row[1]):
                trace.night_kills += 1
            elif VOTE_ELIMINATION_RE.search(row[1]):
                trace.vote_eliminations += 1

        return evaluate_episode(
            env=env,
            state=state,
            variant_id=label,
            seed=seed,
            num_players=num_players,
            mafia_count=mafia_count,
            trace=trace,
            target_action_format=self.action_format,
            seat_variants=seat_variants,
        )


# ---------------------------------------------------------------------------
# Evaluation (truth is read here and only here, after all decisions are recorded)
# ---------------------------------------------------------------------------


def oracle_action_values(
    *,
    phase: str,
    actor_role: str,
    legal_targets: Sequence[int],
    true_mafia: frozenset[int],
    pending_elimination: int | None,
) -> dict[str, float]:
    """Truth-conditional action values used for action regret (evaluation only).

    ``+1`` marks a faction-optimal target and ``-1`` a faction-worst target.
    """
    kind = ACTION_KIND_BY_PHASE.get(phase)
    if kind is None:
        raise SCKError(f"no oracle defined for phase {phase}")
    values: dict[str, float] = {}
    if kind in {"vote", "mafia_eliminate"}:
        actor_is_mafia = actor_role.lower() == "mafia"
        for target in legal_targets:
            values[f"{kind}:{target}"] = (
                1.0 if (target in true_mafia) != actor_is_mafia else -1.0
            )
    elif kind == "investigate":
        for target in legal_targets:
            values[f"{kind}:{target}"] = 1.0 if target in true_mafia else -1.0
    elif kind == "protect":
        for target in legal_targets:
            values[f"{kind}:{target}"] = (
                1.0
                if pending_elimination is not None and target == pending_elimination
                else 0.0
            )
    return values


def _utterance_discloses(record: DecisionRecord, fact: str) -> bool:
    if not record.utterance:
        return False
    text = record.utterance
    if fact.startswith("role:"):
        return fact.split(":", 1)[1].lower() in text.lower()
    if fact.startswith("mafia_team:"):
        members = fact.split(":", 1)[1].split(",")
        return all(f"Player {m}" in text for m in members)
    if fact.startswith("investigation:"):
        return fact.split(":", 1)[1].replace("=", " ").lower() in text.lower()
    return False


def _role_win_table(
    true_roles: Mapping[int, str], rewards: Mapping[int, int]
) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = {}
    for pid, role in true_roles.items():
        row = table.setdefault(role, {"played": 0, "won": 0})
        row["played"] += 1
        if rewards.get(pid) == 1:
            row["won"] += 1
    return table


def evaluate_episode(
    *,
    env,
    state,
    variant_id: str,
    seed: int,
    num_players: int,
    mafia_count: int,
    trace: EpisodeTrace,
    target_action_format: str = DEFAULT_TARGET_ACTION_FORMAT,
    seat_variants: Mapping[int, VariantConfig] | None = None,
) -> EpisodeEvaluation:
    """Score a finished episode.  Backstage truth is read here only."""
    true_roles = {pid: env.player_roles[pid] for pid in range(num_players)}
    true_mafia = frozenset(pid for pid, role in true_roles.items() if role == "Mafia")
    true_world_id = mafia_world_id(sorted(true_mafia))
    rewards = dict(state.rewards or {})
    reason = ""
    for pid in range(num_players):
        info = state.game_info.get(pid, {})
        if info.get("reason"):
            reason = info["reason"]
            break

    evaluation = EpisodeEvaluation(
        variant_id=variant_id,
        won=bool(rewards.get(0) == 1) if rewards else None,
        utility=float(rewards[0]) if 0 in rewards else None,
    )
    evaluation.metadata.update(
        {
            "seed": seed,
            "num_players": num_players,
            "mafia_count": mafia_count,
            "condition_id": variant_id,
            "seat_policy_by_actor": (
                {str(pid): v.variant_id for pid, v in sorted(seat_variants.items())}
                if seat_variants
                else {}
            ),
            "steps": trace.steps,
            "nights_played": trace.nights_played,
            "invalid_moves": trace.invalid_moves,
            "termination_reason": reason,
            "empty_player_action_messages": trace.empty_player_action_messages,
            "vote_targets_observable": target_action_format == "native",
            "target_action_format": target_action_format,
            "reconstructed_channels": list(trace.reconstructed_channels),
            "focal_actor": 0,
            "focal_role": true_roles[0],
            "true_mafia": sorted(true_mafia),
            "actor_results": [
                {
                    "actor_id": pid,
                    "role": true_roles[pid],
                    "reward": rewards.get(pid),
                    "won": bool(rewards.get(pid) == 1),
                    "decisions": sum(
                        1 for d in trace.decisions if d.actor_id == pid
                    ),
                }
                for pid in range(num_players)
            ],
            "role_wins": _role_win_table(true_roles, rewards),
            "village_won": bool(
                all(
                    rewards.get(pid) == 1
                    for pid, role in true_roles.items()
                    if role != "Mafia"
                )
            ),
            "decision_count": len(trace.decisions),
            "unavailable_metrics": [
                "persuasion_delta",
                "learned_evidence_likelihoods",
                "vote_target_evidence",
            ],
        }
    )

    # ---- belief calibration (village side only) ------------------------
    # A Mafia actor's belief is a point mass on its own team by construction, so
    # including it would report a meaningless perfect Brier score.  Calibration is
    # measured over the actors that actually have to infer alignment.
    for record in trace.decisions:
        if record.belief is None or true_roles[record.actor_id] == "Mafia":
            continue
        if true_world_id not in record.belief.hypotheses:
            continue
        # Snapshot: the live belief keeps updating for the rest of the episode.
        evaluation.belief_checkpoints.append(
            BeliefCheckpoint(
                step_id=f"{record.step_id}-{true_roles[record.actor_id]}",
                belief=BeliefState(dict(record.belief.hypotheses)),
                true_hypothesis=true_world_id,
            )
        )

    # ---- action regret -------------------------------------------------
    for record in trace.decisions:
        if record.target is None or record.phase not in TARGET_PHASES:
            continue
        legal = record.legal_targets or (record.target,)
        values = oracle_action_values(
            phase=record.phase,
            actor_role=true_roles[record.actor_id],
            legal_targets=legal,
            true_mafia=true_mafia,
            pending_elimination=trace.evaluation_only_pending_elimination_by_step.get(
                record.step_id
            ),
        )
        if record.chosen_action_id not in values:
            values[record.chosen_action_id] = 0.0
        evaluation.action_checkpoints.append(
            ActionCheckpoint(
                step_id=record.step_id,
                chosen_action_id=record.chosen_action_id,
                action_values=values,
            )
        )

    # ---- communication leakage ----------------------------------------
    for record in trace.decisions:
        if not record.protected_facts:
            continue
        disclosed = tuple(
            fact
            for fact in record.protected_facts
            if _utterance_discloses(record, fact)
        )
        evaluation.communication_checkpoints.append(
            CommunicationCheckpoint(
                step_id=record.step_id,
                protected_facts=record.protected_facts,
                disclosed_facts=disclosed,
            )
        )

    return evaluation
