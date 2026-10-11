from narrative.longform.storybox_game_director_v17 import (
    GameDesignSpec,
    audit_game_design,
    mechanic_overlap_penalty,
)


def test_investigation_game_can_pass_high_skill_gate():
    spec = GameDesignSpec(
        game_id="g1",
        objective="reconstruct cause",
        primary_mechanics=[
            "asymmetric_information",
            "investigation_clue_economy",
            "public_evidence_trail",
            "map_unlock",
            "phase_clock",
        ],
        public_evidence_rate=0.58,
        private_information_density=0.63,
        moderator_discretion=0.22,
        strategic_branching=3,
        counterplay_paths=2,
        evidence_redundancy=3,
        dominant_actor_share=0.38,
        stochasticity=0.08,
        action_budget_pressure=0.58,
        deadline_pressure=0.72,
    )
    audit = audit_game_design(spec)
    assert audit.passed
    assert audit.scores["inferential_leverage"] > 0.6


def test_scripted_one_path_game_is_rejected():
    spec = GameDesignSpec(
        game_id="g2",
        objective="find the answer",
        primary_mechanics=["investigation_clue_economy"],
        strategic_branching=1,
        counterplay_paths=0,
    )
    audit = audit_game_design(spec)
    assert not audit.passed
    assert any("one meaningful strategy branch" in x for x in audit.hard_failures)


def test_high_moderator_discretion_is_rejected():
    spec = GameDesignSpec(
        game_id="g3",
        objective="deduce hidden interest",
        primary_mechanics=["hidden_interest", "asymmetric_information"],
        moderator_discretion=0.9,
        strategic_branching=3,
        counterplay_paths=2,
    )
    audit = audit_game_design(spec)
    assert not audit.passed
    assert any("moderator discretion" in x for x in audit.hard_failures)


def test_one_actor_cannot_control_almost_everything():
    spec = GameDesignSpec(
        game_id="g4",
        objective="approve a joint decision",
        primary_mechanics=["proposal_vote_mission", "phase_clock"],
        strategic_branching=3,
        counterplay_paths=2,
        dominant_actor_share=0.8,
    )
    audit = audit_game_design(spec)
    assert not audit.passed
    assert any("one actor controls too much" in x for x in audit.hard_failures)


def test_arc_mechanic_overlap_detects_reskinned_games():
    games = [
        GameDesignSpec(
            game_id=f"g{i}",
            objective="x",
            primary_mechanics=[
                "asymmetric_information",
                "investigation_clue_economy",
                "public_evidence_trail",
            ],
            strategic_branching=2,
            counterplay_paths=1,
        )
        for i in range(3)
    ]
    result = mechanic_overlap_penalty(games)
    assert result["average_overlap"] == 1.0
    assert result["penalty"] > 0.9
