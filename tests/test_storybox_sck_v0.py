from copy import deepcopy

from narrative.longform.storybox_sck_v0 import (
    BeliefState,
    EvidenceRecord,
    OpponentModel,
    StrategicCognitionKernel,
    StrategicObservation,
)
from narrative.longform.storybox_textarena_secret_mafia_adapter_v0 import (
    PHASE_DAY_VOTING,
    SecretMafiaVisibleState,
    TextArenaSecretMafiaAdapter,
    evidence_from_known_alignment,
    initial_mafia_world_belief,
    marginal_mafia_probabilities,
)


def test_hidden_world_belief_enumerates_consistent_role_assignments():
    belief = initial_mafia_world_belief(
        num_players=6,
        actor_id=0,
        actor_role="Villager",
        mafia_count=2,
    )

    # Actor 0 knows they are not mafia, so choose two mafia from the other five.
    assert len(belief.hypotheses) == 10
    assert abs(sum(belief.hypotheses.values()) - 1.0) < 1e-12
    marginals = marginal_mafia_probabilities(belief, 6)
    assert marginals[0] == 0.0
    assert abs(sum(marginals.values()) - 2.0) < 1e-12


def test_hard_alignment_evidence_collapses_hidden_world_mass():
    belief = initial_mafia_world_belief(
        num_players=6,
        actor_id=0,
        actor_role="Detective",
        mafia_count=2,
    )
    evidence = evidence_from_known_alignment(
        evidence_id="night1-investigate-3",
        source="detective_private_result",
        target_player=3,
        is_mafia=True,
        current_belief=belief,
        reliability=1.0,
    )
    belief.update(evidence)

    marginals = marginal_mafia_probabilities(belief, 6)
    assert marginals[3] > 0.999999


def test_noninformative_accusation_does_not_move_belief():
    belief = BeliefState({"world:a": 0.5, "world:b": 0.5})
    prior = deepcopy(belief.hypotheses)
    belief.update(
        EvidenceRecord(
            evidence_id="loud-accusation",
            source="public_speech",
            likelihood_ratio_by_hypothesis={"world:a": 8.0, "world:b": 0.1},
            reliability=1.0,
            informative=False,
            description="Accusation with no independently informative content",
        )
    )

    assert belief.hypotheses == prior
    assert belief.evidence_ledger[-1]["informative"] is False


def test_two_ply_planner_prefers_robust_action_under_hidden_world_risk():
    observation = StrategicObservation(
        actor_id="0",
        game_id="g",
        scene_id="s",
        round_no=1,
        phase="vote",
        visible_public_state={},
        visible_private_state={},
        legal_actions=(
            {
                "action_id": "safe",
                "kind": "vote",
                "opponent_legal_actions": {"1": ["agree", "oppose"]},
            },
            {
                "action_id": "risky",
                "kind": "vote",
                "opponent_legal_actions": {"1": ["agree", "oppose"]},
            },
        ),
    )
    belief = BeliefState({"benign": 0.5, "hostile": 0.5})
    opponent = OpponentModel("1")

    def rollout(obs, action, hypothesis, opponent_id, response_id):
        if action["action_id"] == "safe":
            return 0.60
        if hypothesis == "benign":
            return 1.00 if response_id == "agree" else 0.80
        return -0.20 if response_id == "agree" else -0.40

    kernel = StrategicCognitionKernel(risk_aversion=0.25)
    decision = kernel.decide(observation, belief, {"1": opponent}, rollout)

    assert decision.action_id == "safe"
    assert len(decision.planning_trace) == 2
    assert decision.uncertainty == 0.0


def test_secret_mafia_adapter_emits_textarena_vote_format():
    adapter = TextArenaSecretMafiaAdapter()
    state = SecretMafiaVisibleState(
        actor_id=0,
        num_players=6,
        phase=PHASE_DAY_VOTING,
        day_number=1,
        alive_players=[0, 1, 2, 3, 4, 5],
        actor_role="Villager",
    )
    observation = adapter.to_strategic_observation(state)

    target_action = next(row for row in observation.legal_actions if row["target"] == 3)
    belief = BeliefState({"one-world": 1.0})

    def rollout(obs, action, hypothesis, opponent_id, response_id):
        return 1.0 if action.get("target") == 3 else 0.0

    decision = StrategicCognitionKernel().decide(observation, belief, {}, rollout)
    assert decision.action_id == target_action["action_id"]
    assert adapter.decision_to_textarena_action(decision) == "[Player 3]"
