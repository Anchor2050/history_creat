"""Joint Project under private costs — minimal mixed-motive repeated game for SCK.

Contract: ``docs/adaptation/sck-mixed-motive-benchmark-contract-v1.md``.
This module implements exactly that contract and nothing more.  Parameters are
fixed by the contract and were chosen before any episode was run.

Why an own-authored environment
-------------------------------
A survey of candidate third-party substrates (``tools/probe_mixed_motive_envs.py``)
found none that satisfies the contract: the TextArena environments that actually
run are fully symmetric and contain no hidden variable for the belief layer to
engage, while the one with genuine private valuations (``BlindAuction``) raises
``TypeError`` in ``reset`` on textarena 0.7.4.  An own-authored substrate is
weaker evidence than a third-party environment and every result from it carries
that label.

Information boundary
--------------------
* :class:`AgentView` is frozen and tuple-only and contains only what the contract
  makes public plus the agent's own cost type and its own cumulative payoff.
* Per-agent payoffs are deliberately **not** published: with ``success`` and
  ``x_i`` public, ``payoff_i = success*bonus - c_i*x_i`` would let any observer
  recover ``c_i`` in one division and destroy the inference problem.  Only the
  aggregate surplus is public, so the types stay learnable but uncertain.
* The environment holds the true types in ``_types`` and never places another
  agent's type in any observation, pledge, contribution, payoff or record.
* The full-information optimum is computed only by
  :func:`full_information_optimum`, which the harness calls during evaluation.

Determinism
-----------
A single ``random.Random(seed)`` owned by the environment draws the cost types.
Policies never receive the environment and use their own RNGs, so a policy cannot
perturb environment randomness.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
import random
from typing import Any, Mapping, Sequence

SCK_ENV_ERROR = ValueError


class JointProjectError(SCK_ENV_ERROR):
    pass


PHASE_PLEDGE = "pledge"
PHASE_CONTRIBUTE = "contribute"
PHASES = (PHASE_PLEDGE, PHASE_CONTRIBUTE)

TYPE_VALUES = (1, 2, 4)
TYPE_PROBABILITIES = (0.4, 0.4, 0.2)


@dataclass(frozen=True)
class JointProjectConfig:
    """Contract-fixed parameters.  Do not edit in place; make a new contract version."""

    num_agents: int = 4
    rounds: int = 8
    threshold: int = 6
    bonus: int = 6
    max_contribution: int = 3
    type_values: tuple[int, ...] = TYPE_VALUES
    type_probabilities: tuple[float, ...] = TYPE_PROBABILITIES

    def __post_init__(self) -> None:
        if self.num_agents != 4:
            raise JointProjectError(
                "contract v1 fixes 4 agents; changing it needs a new contract version"
            )
        if self.rounds != 8:
            raise JointProjectError(
                "contract v1 fixes 8 rounds; changing it needs a new contract version"
            )
        if (self.threshold, self.bonus, self.max_contribution) != (6, 6, 3):
            raise JointProjectError(
                "contract v1 fixes threshold=6, bonus=6, max_contribution=3"
            )
        if self.type_values != TYPE_VALUES or self.type_probabilities != TYPE_PROBABILITIES:
            raise JointProjectError("contract v1 fixes the type values and probabilities")
        if abs(sum(self.type_probabilities) - 1.0) > 1e-9:
            raise JointProjectError("type probabilities must sum to 1")

    @property
    def legal_values(self) -> tuple[int, ...]:
        return tuple(range(self.max_contribution + 1))


@dataclass(frozen=True)
class RoundRecord:
    """A finished round's public record.

    Deliberately excludes per-agent payoffs.  ``payoff_i = success*bonus - c_i*x_i``
    with both ``success`` and ``x_i`` public would let any observer recover
    ``c_i`` in one division, which would destroy the inference problem the
    benchmark exists to create.  Only the aggregate surplus is published, so the
    hidden types are learnable through one linear equation per round and stay
    uncertain for several rounds.
    """

    round_index: int
    pledges: tuple[tuple[int, int], ...]
    contributions: tuple[tuple[int, int], ...]
    success: bool
    total_surplus: float
    pledge_broken: tuple[int, ...]


@dataclass(frozen=True)
class AgentView:
    """Everything one agent may legitimately know at one phase of one round."""

    agent_id: int
    num_agents: int
    round_index: int
    rounds_total: int
    phase: str
    threshold: int
    bonus: int
    max_contribution: int
    type_values: tuple[int, ...]
    type_probabilities: tuple[float, ...]
    own_type: int
    own_cumulative_payoff: float
    legal_values: tuple[int, ...]
    public_history: tuple[RoundRecord, ...]
    pledges_this_round: tuple[tuple[int, int], ...]
    pledges_kept: tuple[tuple[int, int], ...]
    pledges_broken: tuple[tuple[int, int], ...]

    @property
    def other_agents(self) -> tuple[int, ...]:
        return tuple(a for a in range(self.num_agents) if a != self.agent_id)

    def record_for(self, agent_id: int) -> RoundRecord | None:
        for record in self.public_history:
            if agent_id in dict(record.contributions):
                return record
        return None

    def surplus_history(self) -> tuple[float, ...]:
        return tuple(record.total_surplus for record in self.public_history)


def assert_information_safe(view: AgentView) -> None:
    """Fail loudly if a decision view ever exposes another agent's cost type."""
    forbidden = ("types", "other_types", "true_types", "full_information_optimum")
    for name in forbidden:
        if hasattr(view, name):
            raise JointProjectError(f"agent view leaks backstage attribute: {name}")
    if view.own_type not in view.type_values:
        raise JointProjectError("agent view carries a type outside the value set")


@dataclass
class JointProjectEnv:
    """Simultaneous-phase repeated joint-project game with private persistent costs."""

    config: JointProjectConfig = field(default_factory=JointProjectConfig)
    _types: tuple[int, ...] = ()
    _round_index: int = 0
    _phase: str = PHASE_PLEDGE
    _pledges: dict[int, int] = field(default_factory=dict)
    _contributions: dict[int, int] = field(default_factory=dict)
    _history: list[RoundRecord] = field(default_factory=list)
    _cumulative: dict[int, float] = field(default_factory=dict)
    _kept: dict[int, int] = field(default_factory=dict)
    _broken: dict[int, int] = field(default_factory=dict)
    _rng: random.Random | None = None
    done: bool = False

    # -- lifecycle -------------------------------------------------------
    def reset(self, *, seed: int) -> None:
        self._rng = random.Random(seed)
        self._types = tuple(
            self._rng.choices(
                list(self.config.type_values),
                weights=list(self.config.type_probabilities),
                k=self.config.num_agents,
            )
        )
        self._round_index = 0
        self._phase = PHASE_PLEDGE
        self._pledges = {}
        self._contributions = {}
        self._history = []
        self._cumulative = {i: 0.0 for i in range(self.config.num_agents)}
        self._kept = {i: 0 for i in range(self.config.num_agents)}
        self._broken = {i: 0 for i in range(self.config.num_agents)}
        self.done = False

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def round_index(self) -> int:
        return self._round_index

    @property
    def history(self) -> tuple[RoundRecord, ...]:
        return tuple(self._history)

    def true_types(self) -> tuple[int, ...]:
        """Backstage truth.  Evaluation and calibration labels only, never a view."""
        return self._types

    # -- observation -----------------------------------------------------
    def observe(self, agent_id: int) -> AgentView:
        if not 0 <= agent_id < self.config.num_agents:
            raise JointProjectError(f"unknown agent id: {agent_id}")
        if self.done:
            raise JointProjectError("cannot observe a finished episode")
        view = AgentView(
            agent_id=agent_id,
            num_agents=self.config.num_agents,
            round_index=self._round_index,
            rounds_total=self.config.rounds,
            phase=self._phase,
            threshold=self.config.threshold,
            bonus=self.config.bonus,
            max_contribution=self.config.max_contribution,
            type_values=tuple(self.config.type_values),
            type_probabilities=tuple(self.config.type_probabilities),
            own_type=int(self._types[agent_id]),
            own_cumulative_payoff=float(self._cumulative[agent_id]),
            legal_values=self.config.legal_values,
            public_history=tuple(self._history),
            pledges_this_round=tuple(sorted(self._pledges.items())),
            pledges_kept=tuple(sorted(self._kept.items())),
            pledges_broken=tuple(sorted(self._broken.items())),
        )
        assert_information_safe(view)
        return view

    # -- resolution ------------------------------------------------------
    def resolve(self, actions: Mapping[int, int]) -> dict[str, Any]:
        """Apply one phase's simultaneous submissions and advance.

        Returns a small event dict describing what became public.  The caller
        must supply exactly one action per agent.
        """
        if self.done:
            raise JointProjectError("episode already finished")
        expected = set(range(self.config.num_agents))
        supplied = {int(k) for k in actions}
        if supplied != expected:
            raise JointProjectError(
                f"expected an action for every agent; missing {sorted(expected - supplied)}"
            )
        legal = set(self.config.legal_values)
        cleaned: dict[int, int] = {}
        for agent_id, value in actions.items():
            value = int(value)
            if value not in legal:
                raise JointProjectError(
                    f"agent {agent_id} chose {value}, outside {sorted(legal)}"
                )
            cleaned[int(agent_id)] = value

        if self._phase == PHASE_PLEDGE:
            self._pledges = cleaned
            self._phase = PHASE_CONTRIBUTE
            return {
                "event": "pledges_published",
                "round_index": self._round_index,
                "pledges": dict(sorted(cleaned.items())),
            }

        self._contributions = cleaned
        record = self._resolve_round()
        self._history.append(record)
        self._phase = PHASE_PLEDGE
        self._pledges = {}
        self._contributions = {}
        self._round_index += 1
        if self._round_index >= self.config.rounds:
            self.done = True
        return {
            "event": "round_resolved",
            "round_index": record.round_index,
            "contributions": dict(record.contributions),
            "success": record.success,
            "total_surplus": record.total_surplus,
            "pledge_broken": list(record.pledge_broken),
        }

    def _resolve_round(self) -> RoundRecord:
        total = sum(self._contributions.values())
        success = total >= self.config.threshold
        payoffs: dict[int, float] = {}
        for agent_id in range(self.config.num_agents):
            contributed = self._contributions[agent_id]
            gain = float(self.config.bonus) if success else 0.0
            payoffs[agent_id] = gain - self._types[agent_id] * contributed
            self._cumulative[agent_id] += payoffs[agent_id]
        broken = tuple(
            sorted(
                agent_id
                for agent_id in range(self.config.num_agents)
                if self._pledges.get(agent_id, 0) != self._contributions[agent_id]
            )
        )
        for agent_id in range(self.config.num_agents):
            if agent_id in broken:
                self._broken[agent_id] += 1
            else:
                self._kept[agent_id] += 1
        return RoundRecord(
            round_index=self._round_index,
            pledges=tuple(sorted(self._pledges.items())),
            contributions=tuple(sorted(self._contributions.items())),
            success=success,
            total_surplus=float(sum(payoffs.values())),
            pledge_broken=broken,
        )

    # -- evaluation helpers ---------------------------------------------
    def total_payoffs(self) -> dict[int, float]:
        return dict(self._cumulative)


# ---------------------------------------------------------------------------
# Evaluation-only oracles
# ---------------------------------------------------------------------------


def round_joint_surplus(
    *, contributions: Sequence[int], types: Sequence[int], config: JointProjectConfig
) -> float:
    total = sum(int(x) for x in contributions)
    success = total >= config.threshold
    gain = float(config.bonus) if success else 0.0
    return sum(gain - int(c) * int(x) for c, x in zip(types, contributions))


def full_information_optimum(
    *, types: Sequence[int], config: JointProjectConfig
) -> tuple[float, tuple[int, ...]]:
    """Best achievable joint surplus given the true types.  Evaluation only."""
    if len(types) != config.num_agents:
        raise JointProjectError("types length must match num_agents")
    best_value = float("-inf")
    best_plan: tuple[int, ...] = tuple(0 for _ in types)
    for plan in product(config.legal_values, repeat=config.num_agents):
        value = round_joint_surplus(
            contributions=plan, types=types, config=config
        )
        if value > best_value:
            best_value = value
            best_plan = tuple(int(x) for x in plan)
    return best_value, best_plan


def best_own_contribution_given_realised_others(
    *,
    own_type: int,
    others_contributions: Sequence[int],
    config: JointProjectConfig,
) -> int:
    """Legitimate post-hoc counterfactual for the regret diagnostic.

    Uses only information available after the round: the agent's own type and the
    other agents' realised contributions.  It never uses the full-information
    optimum, which would not be a legitimate decision-time comparison.
    """
    base = sum(int(x) for x in others_contributions)
    best_value = float("-inf")
    best_action = 0
    for action in config.legal_values:
        success = base + action >= config.threshold
        gain = float(config.bonus) if success else 0.0
        value = gain - own_type * action
        if value > best_value:
            best_value = value
            best_action = action
    return best_action
