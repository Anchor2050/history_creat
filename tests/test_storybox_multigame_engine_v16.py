from narrative.longform.storybox_multigame_engine_v16 import (
    ActorPortfolio,
    EventArcState,
    EventNode,
    GameParticipation,
    GameRuntime,
    MultiGameEngineError,
    MultiGameWorldState,
    SceneState,
    append_round_to_scene,
    end_scene,
    evaluate_event_node,
    fire_event_node,
    game_local_role,
    join_game,
    participation_load,
    register_scene,
    apply_cross_game_spillover,
)


def _world_with_two_games(actor_portfolios):
    arc = EventArcState(
        event_arc_id="arc:risk",
        games={
            "game:cause": GameRuntime(
                game_id="game:cause",
                event_arc_id="arc:risk",
                objective="reconstruct causal chain",
            ),
            "game:briefing": GameRuntime(
                game_id="game:briefing",
                event_arc_id="arc:risk",
                objective="decide what can be reported",
            ),
        },
        scenes={},
        event_nodes={},
    )
    return MultiGameWorldState(actor_portfolios=actor_portfolios, event_arcs={"arc:risk": arc})


def test_same_actor_can_have_different_local_roles_without_global_moral_label():
    p = ActorPortfolio(actor_id="zhou", max_parallel_games_soft=2, max_parallel_games_hard=3)
    p = join_game(
        p,
        GameParticipation(
            game_id="game:cause",
            local_role="technical_verifier",
            local_stake="reconstruct exact run",
            stance="push_for_reproducible_evidence",
            attention=0.45,
        ),
    )
    p = join_game(
        p,
        GameParticipation(
            game_id="game:briefing",
            local_role="vendor_representative",
            local_stake="avoid unsupported liability claim",
            stance="resist_premature_public_causality",
            attention=0.35,
        ),
    )
    world = _world_with_two_games({"zhou": p})

    cause = game_local_role(world, "zhou", "game:cause")
    briefing = game_local_role(world, "zhou", "game:briefing")

    assert cause["local_role"] == "technical_verifier"
    assert briefing["local_role"] == "vendor_representative"
    assert cause["stance"] != briefing["stance"]
    assert "good" not in cause and "bad" not in cause


def test_soft_capacity_overflow_is_legal_but_adds_fatigue():
    p = ActorPortfolio(
        actor_id="director",
        attention_budget=1.0,
        max_parallel_games_soft=1,
        max_parallel_games_hard=4,
        delegation_capacity=0.6,
        coordination_capacity=0.8,
        overload_penalty_per_slot=0.2,
    )
    for idx in range(3):
        p = join_game(
            p,
            GameParticipation(
                game_id=f"game:{idx}",
                local_role="decision_owner",
                local_stake="institutional outcome",
                stance="active",
                attention=0.35,
            ),
        )
    load = participation_load(p)
    assert load["active_game_count"] == 3
    assert load["soft_game_overflow"] == 2
    assert p.current_fatigue > 0


def test_hard_parallel_game_cap_cannot_be_exceeded():
    p = ActorPortfolio(actor_id="ordinary", max_parallel_games_soft=1, max_parallel_games_hard=2)
    for idx in range(2):
        p = join_game(
            p,
            GameParticipation(
                game_id=f"game:{idx}",
                local_role="participant",
                local_stake="local",
                stance="active",
                attention=0.3,
            ),
        )
    try:
        join_game(
            p,
            GameParticipation(
                game_id="game:2",
                local_role="participant",
                local_stake="local",
                stance="active",
                attention=0.2,
            ),
        )
        assert False, "expected hard-cap error"
    except MultiGameEngineError:
        pass


def test_scene_contains_multiple_rounds_before_it_ends():
    p = ActorPortfolio(actor_id="luo", max_parallel_games_hard=2)
    p = join_game(
        p,
        GameParticipation(
            game_id="game:cause",
            local_role="process_coordinator",
            local_stake="preserve audit chain",
            stance="collect_facts",
            attention=0.7,
        ),
    )
    world = _world_with_two_games({"luo": p})
    scene = SceneState(
        scene_id="scene:office:01",
        event_arc_id="arc:risk",
        game_id="game:cause",
        trigger={"kind": "suspicious_list"},
        location="project_office",
        channel="in_person",
        participants=["luo"],
        local_objectives=["identify which batch produced the leaked screenshot"],
    )
    world = register_scene(world, scene)
    s = world.event_arcs["arc:risk"].scenes["scene:office:01"]
    s = append_round_to_scene(s, {"round_no": 1, "delta": "screenshot predates current batch"})
    s = append_round_to_scene(s, {"round_no": 2, "delta": "freeze all overnight batches"})
    s = end_scene(
        s,
        reason="new_evidence_changes_action_set",
        unresolved_carry=["reconstruct overnight runs"],
    )
    assert len(s.rounds) == 2
    assert s.status == "ended"
    assert s.unresolved_carry == ["reconstruct overnight runs"]


def test_cross_game_spillover_requires_explicit_bridge():
    p = ActorPortfolio(actor_id="zhou", max_parallel_games_soft=2, max_parallel_games_hard=3)
    for gid in ("game:cause", "game:briefing"):
        p = join_game(
            p,
            GameParticipation(
                game_id=gid,
                local_role="participant",
                local_stake="shared incident",
                stance="active",
                attention=0.3,
            ),
        )
    world = _world_with_two_games({"zhou": p})
    world = apply_cross_game_spillover(
        world,
        actor_id="zhou",
        source_game_id="game:cause",
        target_game_id="game:briefing",
        domain="public_information",
        value={"fact": "rollback confirmed"},
        bridge="formal_joint_report",
        evidence="signed incident note",
    )
    assert world.spillover_history[-1]["bridge"] == "formal_joint_report"


def test_event_node_cannot_fire_before_game_preconditions():
    p = ActorPortfolio(actor_id="luo")
    arc = EventArcState(
        event_arc_id="arc:risk",
        games={
            "game:cause": GameRuntime("game:cause", "arc:risk", "cause", status="active"),
            "game:briefing": GameRuntime("game:briefing", "arc:risk", "brief", status="active"),
        },
        scenes={},
        event_nodes={
            "event:joint_briefing": EventNode(
                node_id="event:joint_briefing",
                description="72-hour joint briefing can be issued",
                predicates=[
                    {"path": ["games", "game:cause", "status"], "op": "eq", "value": "resolved"},
                    {"path": ["games", "game:briefing", "status"], "op": "eq", "value": "resolved"},
                ],
                fires_world_deltas=[
                    {"path": ["risk_list", "joint_briefing_issued"], "value": True}
                ],
            )
        },
    )
    world = MultiGameWorldState(actor_portfolios={"luo": p}, event_arcs={"arc:risk": arc})
    result = evaluate_event_node(world, "arc:risk", "event:joint_briefing")
    assert result["ready"] is False

    world.event_arcs["arc:risk"].games["game:cause"].status = "resolved"
    world.event_arcs["arc:risk"].games["game:briefing"].status = "resolved"
    result = evaluate_event_node(world, "arc:risk", "event:joint_briefing")
    assert result["ready"] is True

    world = fire_event_node(world, "arc:risk", "event:joint_briefing")
    assert world.global_state["risk_list"]["joint_briefing_issued"] is True
    assert "event:joint_briefing" in world.event_arcs["arc:risk"].fired_nodes
