"""Tests for the live TextArena SecretMafia runner and its information boundary.

The offline tests use no external dependency.  The live tests are skipped when
``textarena`` is not importable, so this file runs both in the plain project
interpreter and in the dedicated TextArena environment.
"""
import ast
import copy
import inspect

import pytest

from narrative.longform.storybox_sck_eval_v0 import VariantConfig
from narrative.longform.storybox_sck_v0 import BeliefState, SCKError
from narrative.longform.storybox_textarena_secret_mafia_adapter_v0 import (
    PHASE_DAY_DISCUSSION,
    PHASE_DAY_VOTING,
    PHASE_NIGHT_DETECTIVE,
    PHASE_NIGHT_DOCTOR,
    PHASE_NIGHT_MAFIA,
    initial_mafia_world_belief,
    parse_mafia_world,
)
from narrative.longform import storybox_textarena_secret_mafia_live_v0 as live

MAFIA_PROMPT = (
    "Welcome to Secret Mafia! You are Player 1.\n"
    "Your role: Mafia\nTeam: Mafia\nDescription: A Mafia member.\n\n"
    "Players: Player 0, Player 1, Player 2, Player 3, Player 4, Player 5\n\n"
    "Your teammates are: Player 1, Player 2.\n\n"
    "During DAY phase: Speak freely and vote.\n"
)
DETECTIVE_PROMPT = (
    "Welcome to Secret Mafia! You are Player 5.\n"
    "Your role: Detective\nTeam: Village\n\n"
    "Players: Player 0, Player 1, Player 2, Player 3, Player 4, Player 5\n\n"
    "During DAY phase: Speak freely and vote.\n"
)
VILLAGER_PROMPT = (
    "Welcome to Secret Mafia! You are Player 3.\n"
    "Your role: Villager\nTeam: Village\n\n"
    "Players: Player 0, Player 1, Player 2, Player 3, Player 4, Player 5\n\n"
    "The game progresses through Day and Night phases.\n"
)

FORBIDDEN_SUBSTRINGS = ("player_roles", "secret_roles", "pending_elimination")

#: Definitions that participate in producing a decision.  Backstage state must
#: never be read anywhere inside them.  ``evaluate_episode`` is deliberately
#: excluded: scoring is the one place truth is allowed.
AUDITED_DEFINITIONS = (
    "ActorView",
    "assert_information_safe",
    "SecretMafiaPolicy",
    "PlainPolicy",
    "MemoryPolicy",
    "BeliefPolicy",
    "BeliefPlanningPolicy",
    "build_policy",
    "legal_targets_for",
    "parse_role_and_teammates",
    "parse_investigations",
    "night_kill_evidence",
    "doctor_saved_evidence",
    "recorded_vote_evidence",
    "render_discussion",
)

#: The single permitted backstage-name read on the decision path:
#: ``assert_information_safe`` checks that the boundary object it just built has
#: ``pending_elimination is None`` and raises otherwise.  It never uses the value
#: to decide anything, and it is itself covered by
#: ``test_information_guard_rejects_a_view_carrying_backstage_state``.
ALLOWED_BACKSTAGE_READS = {("assert_information_safe", "pending_elimination")}


def _entry(message, *, from_id=-1, kind="GAME_MESSAGE", public=True, phase="Night-Doctor"):
    return live.TranscriptEntry(
        from_id=from_id,
        message=message,
        observation_type=kind,
        phase=phase,
        night_number=1,
        public=public,
    )


# ---------------------------------------------------------------------------
# Parsing and information boundary
# ---------------------------------------------------------------------------


def test_prompt_parsing_recovers_role_and_mafia_team_from_private_prompt():
    assert live.parse_role_and_teammates(MAFIA_PROMPT) == ("Mafia", (1, 2))
    assert live.parse_role_and_teammates(DETECTIVE_PROMPT) == ("Detective", ())
    assert live.parse_role_and_teammates(VILLAGER_PROMPT) == ("Villager", ())


def test_mafia_prompt_without_teammates_is_rejected():
    with pytest.raises(SCKError):
        live.parse_role_and_teammates("Your role: Mafia\nTeam: Mafia\n")


def test_legal_targets_never_include_the_mafia_team():
    targets = live.legal_targets_for(
        role="Mafia",
        phase=PHASE_NIGHT_MAFIA,
        alive_players=[0, 1, 2, 3, 4, 5],
        mafia_teammates=[1, 2],
        actor_id=1,
    )
    assert targets == (0, 3, 4, 5)


def test_legal_targets_exclude_self_for_voting_and_night_power_roles():
    for phase in (PHASE_NIGHT_DOCTOR, PHASE_NIGHT_DETECTIVE, PHASE_DAY_VOTING):
        targets = live.legal_targets_for(
            role="Doctor",
            phase=phase,
            alive_players=[0, 1, 2],
            mafia_teammates=(),
            actor_id=1,
        )
        assert targets == (0, 2)
    assert live.legal_targets_for(
        role="Villager",
        phase=PHASE_DAY_DISCUSSION,
        alive_players=[0, 1],
        mafia_teammates=(),
        actor_id=0,
    ) == ()


def test_vote_tag_parsing_matches_the_environment_voting_pattern():
    assert live.parse_vote_target("[Player 3]") == 3
    assert live.parse_vote_target("[3]") == 3
    assert live.parse_vote_target("[player 12]") == 12
    assert live.parse_vote_target("I have nothing to add.") is None


def test_actor_view_is_frozen_and_exposes_no_backstage_attribute():
    view = live.ActorView(
        actor_id=3,
        num_players=6,
        mafia_count=2,
        role="Villager",
        mafia_teammates=(),
        phase=PHASE_DAY_VOTING,
        night_number=1,
        alive_players=(0, 1, 2, 3, 4, 5),
        legal_targets=(0, 1, 2, 4, 5),
        discussion_turn=1,
        pending=(_entry("Day breaks."),),
        history=(_entry(VILLAGER_PROMPT, kind="PROMPT", public=False),),
        own_actions=(),
        investigations=(),
    )
    for name in live.FORBIDDEN_VIEW_ATTRIBUTES:
        assert not hasattr(view, name)
    live.assert_information_safe(view)
    with pytest.raises(Exception):
        view.role = "Mafia"  # frozen dataclass

    visible = view.as_visible_state(live.TextArenaSecretMafiaAdapter())
    assert visible.pending_elimination is None
    assert visible.known_mafia == []


def test_information_guard_rejects_a_view_carrying_backstage_state():
    class LeakyView(live.ActorView):
        player_roles = {0: "Mafia"}

    view = LeakyView(
        actor_id=0,
        num_players=6,
        mafia_count=2,
        role="Mafia",
        mafia_teammates=(0,),
        phase=PHASE_NIGHT_MAFIA,
        night_number=1,
        alive_players=(0, 1, 2),
        legal_targets=(1, 2),
        discussion_turn=1,
        pending=(),
        history=(),
        own_actions=(),
        investigations=(),
    )
    with pytest.raises(SCKError):
        live.assert_information_safe(view)


def test_policy_and_runner_sources_never_read_backstage_state_before_evaluation():
    """Static audit: decision-path code never reads a backstage field.

    Reading means attribute access (``state.player_roles``), subscripting with a
    forbidden key (``game_state["secret_roles"]``) or passing a forbidden keyword
    argument a real value.  Explicitly passing ``None`` for
    ``pending_elimination`` is the boundary being *created*, not violated.
    """
    tree = ast.parse(inspect.getsource(live))
    audited = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        and node.name in AUDITED_DEFINITIONS
    }
    assert set(audited) == set(AUDITED_DEFINITIONS), (
        f"audit list out of date: {sorted(set(AUDITED_DEFINITIONS) - set(audited))}"
    )
    offenders = []
    for name, node in audited.items():
        for child in ast.walk(node):
            hits = []
            if isinstance(child, ast.Attribute) and child.attr in FORBIDDEN_SUBSTRINGS:
                hits.append(child.attr)
            if (
                isinstance(child, ast.Subscript)
                and isinstance(child.slice, ast.Constant)
                and child.slice.value in FORBIDDEN_SUBSTRINGS
            ):
                hits.append(str(child.slice.value))
            if isinstance(child, ast.keyword) and child.arg in FORBIDDEN_SUBSTRINGS:
                if not (
                    isinstance(child.value, ast.Constant) and child.value.value is None
                ):
                    hits.append(child.arg)
            for hit in hits:
                if (name, hit) not in ALLOWED_BACKSTAGE_READS:
                    offenders.append(f"{name}:{hit}")
    assert offenders == [], f"backstage access on the decision path: {offenders}"


# ---------------------------------------------------------------------------
# Evidence model
# ---------------------------------------------------------------------------


def _village_belief():
    return initial_mafia_world_belief(
        num_players=6, actor_id=0, actor_role="Villager", mafia_count=2
    )


def test_night_kill_evidence_downweights_worlds_where_the_victim_is_mafia():
    belief = _village_belief()
    before = live.marginal_mafia_probabilities(belief, 6)[3]
    belief.update(
        live.night_kill_evidence(
            evidence_id="kill-3",
            victim=3,
            belief=belief,
            model=live.BehaviorEvidenceModel(),
        )
    )
    after = live.marginal_mafia_probabilities(belief, 6)[3]
    assert after < before
    # The update is soft (likelihood 0.02 at reliability 0.95), so the victim
    # retains only trace mass rather than being hard-excluded.
    assert after < before * 0.1
    assert abs(sum(belief.hypotheses.values()) - 1.0) < 1e-12
    assert any(3 not in parse_mafia_world(w) for w in belief.hypotheses)


def test_doctor_saved_evidence_downweights_the_protected_player():
    belief = initial_mafia_world_belief(
        num_players=6, actor_id=0, actor_role="Doctor", mafia_count=2
    )
    before = live.marginal_mafia_probabilities(belief, 6)[4]
    belief.update(
        live.doctor_saved_evidence(
            evidence_id="save-4",
            protected=4,
            belief=belief,
            model=live.BehaviorEvidenceModel(),
        )
    )
    after = live.marginal_mafia_probabilities(belief, 6)[4]
    assert after < before


def test_recorded_vote_evidence_only_moves_worlds_where_the_voter_is_mafia():
    belief = _village_belief()
    belief.update(
        live.recorded_vote_evidence(
            evidence_id="vote-1-2",
            voter=1,
            target=2,
            belief=belief,
            model=live.BehaviorEvidenceModel(),
        )
    )
    # Worlds where 1 is Mafia must be down-weighted relative to worlds where it is not.
    mafia_voter_mass = sum(
        p for w, p in belief.hypotheses.items() if 1 in parse_mafia_world(w)
    )
    assert mafia_voter_mass < 2 / 5


def test_noninformative_and_zero_reliability_evidence_do_not_move_belief():
    belief = _village_belief()
    prior = copy.deepcopy(belief.hypotheses)
    belief.update(
        live.night_kill_evidence(
            evidence_id="kill-3",
            victim=3,
            belief=belief,
            model=live.BehaviorEvidenceModel(night_kill_reliability=0.0),
        )
    )
    assert belief.hypotheses == prior


# ---------------------------------------------------------------------------
# Language boundary
# ---------------------------------------------------------------------------


def test_discussion_renderer_never_emits_vote_syntax():
    view = live.ActorView(
        actor_id=0,
        num_players=6,
        mafia_count=2,
        role="Villager",
        mafia_teammates=(),
        phase=PHASE_DAY_DISCUSSION,
        night_number=2,
        alive_players=(0, 1, 2, 3),
        legal_targets=(),
        discussion_turn=1,
        pending=(),
        history=(),
        own_actions=(),
        investigations=(),
    )
    for target in (None, 3):
        text = live.render_discussion(view, target)
        assert live.parse_vote_target(text) is None
        assert "[" not in text


def test_protected_facts_include_role_and_investigations():
    policy = live.BeliefPolicy(num_players=6, seed=1)
    view = live.ActorView(
        actor_id=5,
        num_players=6,
        mafia_count=2,
        role="Detective",
        mafia_teammates=(),
        phase=PHASE_DAY_VOTING,
        night_number=2,
        alive_players=(0, 1, 5),
        legal_targets=(0, 1),
        discussion_turn=1,
        pending=(),
        history=(),
        own_actions=(),
        investigations=((1, True),),
    )
    facts = policy.protected_facts(view)
    assert "role:Detective" in facts
    assert "investigation:1=mafia" in facts


# ---------------------------------------------------------------------------
# Oracle (evaluation only)
# ---------------------------------------------------------------------------


def test_oracle_punishes_village_for_voting_a_confirmed_villager():
    values = live.oracle_action_values(
        phase=PHASE_DAY_VOTING,
        actor_role="Villager",
        legal_targets=[1, 2, 3],
        true_mafia=frozenset({2}),
        pending_elimination=None,
    )
    assert values["vote:2"] == 1.0
    assert values["vote:1"] == -1.0
    assert values["vote:3"] == -1.0


def test_oracle_mirrors_for_mafia_and_rewards_killing_the_mafia_target():
    mafia_values = live.oracle_action_values(
        phase=PHASE_DAY_VOTING,
        actor_role="Mafia",
        legal_targets=[1, 2],
        true_mafia=frozenset({0, 2}),
        pending_elimination=None,
    )
    assert mafia_values["vote:1"] == 1.0
    assert mafia_values["vote:2"] == -1.0

    protect_values = live.oracle_action_values(
        phase=PHASE_NIGHT_DOCTOR,
        actor_role="Doctor",
        legal_targets=[1, 2, 3],
        true_mafia=frozenset({2}),
        pending_elimination=3,
    )
    assert protect_values["protect:3"] == 1.0
    assert protect_values["protect:1"] == 0.0


def test_live_dependency_is_lazy_and_reports_unavailability_clearly():
    source = inspect.getsource(live)
    assert "import textarena" not in source.split("def load_textarena")[0]
    assert live.DECISION_TIME_STATE_KEYS == ("phase", "day_number", "alive_players")


# ---------------------------------------------------------------------------
# Live episodes (skipped without textarena)
# ---------------------------------------------------------------------------

LIVE_VARIANTS = [
    VariantConfig("plain", False, False, 0, False),
    VariantConfig("memory", True, False, 0, False),
    VariantConfig("belief", True, True, 0, True),
    VariantConfig("belief_planning", True, True, 2, True),
]


def _require_textarena():
    pytest.importorskip("textarena")


@pytest.mark.parametrize("variant", LIVE_VARIANTS, ids=lambda v: v.variant_id)
def test_live_secret_mafia_episode_completes_and_scores(variant):
    _require_textarena()
    runner = live.SecretMafiaLiveRunner(discussion_rounds=1)
    evaluation = runner.run_episode(variant=variant, num_players=6, seed=7)
    summary = evaluation.summary()
    assert summary["metadata"]["decision_count"] > 0
    assert summary["won"] in (True, False)
    assert summary["utility"] in (1.0, -1.0)
    assert summary["mean_action_regret"] is not None
    assert summary["information_leakage_count"] == 0
    assert summary["metadata"]["vote_targets_observable"] is False
    if variant.belief_enabled:
        assert summary["mean_brier"] is not None
    else:
        # Documented unavailable metric rather than a fabricated number.
        assert summary["mean_brier"] is None
    assert len(summary["metadata"]["role_wins"]) >= 3


def test_live_episode_is_deterministic_for_a_fixed_seed():
    _require_textarena()
    runner = live.SecretMafiaLiveRunner(discussion_rounds=1)
    first = runner.run_episode(variant=LIVE_VARIANTS[2], num_players=6, seed=3)
    second = runner.run_episode(variant=LIVE_VARIANTS[2], num_players=6, seed=3)
    assert first.metadata["true_mafia"] == second.metadata["true_mafia"]
    assert first.metadata["steps"] == second.metadata["steps"]
    assert first.metadata["termination_reason"] == second.metadata["termination_reason"]
    assert [
        row["reward"] for row in first.metadata["actor_results"]
    ] == [row["reward"] for row in second.metadata["actor_results"]]


def test_live_runner_never_uses_the_backstage_pending_target_for_decisions():
    """The oracle uses the pending night target; policies must not."""
    _require_textarena()
    runner = live.SecretMafiaLiveRunner(discussion_rounds=1)
    evaluation = runner.run_episode(variant=LIVE_VARIANTS[3], num_players=6, seed=5)
    protect_steps = [
        row for row in evaluation.action_checkpoints if "protect:" in row.chosen_action_id
    ]
    assert protect_steps, "expected at least one Doctor decision in a 6-player game"


def test_live_actor_views_only_ever_carry_the_actors_own_private_prompt(monkeypatch):
    """Empirical information-boundary check across a whole live episode."""
    _require_textarena()
    seen = []

    class AuditedPlain(live.PlainPolicy):
        def act(self, view):
            live.assert_information_safe(view)
            seen.append(view)
            return super().act(view)

    monkeypatch.setitem(live.POLICY_BY_VARIANT, "plain", AuditedPlain)
    runner = live.SecretMafiaLiveRunner(discussion_rounds=1)
    runner.run_episode(variant=LIVE_VARIANTS[0], num_players=6, seed=13)

    assert len(seen) > 10
    for view in seen:
        prompts = [row for row in view.history if row.observation_type == "PROMPT"]
        assert len(prompts) == 1, "an actor saw more than its own private prompt"
        assert f"You are Player {view.actor_id}." in prompts[0].message
        for row in view.history:
            if row.observation_type == "PROMPT":
                continue
            assert "Your role:" not in row.message
        assert view.role in {"Villager", "Mafia", "Doctor", "Detective"}
