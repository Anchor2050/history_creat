from narrative.longform.storybox_round_engine_v15 import (
    ConvergencePolicy,
    GameState,
    apply_round_resolution,
    build_round_request,
    evaluate_game_convergence,
)


def make_game():
    return GameState(
        game_id="g1",
        objective={"question": "What happened?", "status": "open"},
        hard_world={"secret": "fixed truth"},
        map_state={"unlocked": ["room_a"], "reachable_by_actor": {"a": ["room_a"]}},
        actor_state={"a": {"role": "investigator"}},
        truth={"root_cause": "hidden"},
        public_information={"incident": True},
        private_information={"a": {"clue": "x"}},
        beliefs={"a": {"hypothesis": "maybe_x"}},
        relationships={"a": {}},
        power={"a": {"can_inspect": True}},
        resources={"a": {"time": 1}},
        mysteries={
            "q1": {"question": "Why?", "status": "open", "actionable": True}
        },
        deadlines={"d1": {"status": "active", "remaining_hours": 1}},
        commitments={"a": {}},
        reputation={"a": {}},
        payoff_debt={"q1": {"status": "open"}},
        convergence_policy=ConvergencePolicy(
            min_rounds=2,
            max_rounds=5,
            stable_rounds_required=2,
            max_zero_delta_rounds=2,
        ),
    )


def zero_delta_resolution(request, round_no):
    return {
        "game_id": request["game_id"],
        "round_no": round_no,
        "actions": [
            {
                "action_id": f"a{round_no}",
                "actor": "a",
                "action": "wait",
                "basis": "no new evidence",
            }
        ],
        "state_deltas": [],
        "paid_questions": [],
        "new_questions": [],
        "map_unlocks": [],
        "end_reason": "all_eligible_actors_resolved",
    }


def test_round_request_does_not_leak_truth():
    game = make_game()
    request = build_round_request(game, {"kind": "incident"}, ["a"])

    assert "truth" not in request
    assert request["actors"]["a"]["private_information"] == {"clue": "x"}
    assert request["actors"]["a"]["public_information"] == {"incident": True}


def test_minimum_rounds_prevent_premature_convergence():
    game = make_game()
    result = evaluate_game_convergence(game)

    assert result["continue"] is True
    assert result["reason"] == "minimum_rounds_not_reached"


def test_two_zero_delta_rounds_with_live_pressure_deadlock():
    game = make_game()

    req1 = build_round_request(game, {"kind": "tick"}, ["a"])
    game = apply_round_resolution(game, req1, zero_delta_resolution(req1, 1))

    req2 = build_round_request(game, {"kind": "tick"}, ["a"])
    game = apply_round_resolution(game, req2, zero_delta_resolution(req2, 2))

    result = evaluate_game_convergence(game)

    assert result["continue"] is False
    assert result["converged"] is False
    assert result["reason"] == "deadlock"


def test_objective_resolution_ends_game_even_with_open_mystery():
    game = make_game()
    game.objective["status"] = "resolved"

    result = evaluate_game_convergence(game)

    assert result["continue"] is False
    assert result["converged"] is True
    assert result["reason"] == "objective_resolved"


def test_round_can_pay_old_question_and_open_downstream_question():
    game = make_game()
    request = build_round_request(game, {"kind": "new_log"}, ["a"])
    resolution = {
        "game_id": "g1",
        "round_no": 1,
        "actions": [
            {
                "action_id": "inspect-log",
                "actor": "a",
                "action": "inspect",
                "basis": "new log became available",
            }
        ],
        "state_deltas": [
            {
                "domain": "beliefs",
                "path": ["a", "hypothesis"],
                "value": "version alone is insufficient",
                "evidence": "log comparison",
            }
        ],
        "paid_questions": ["q1"],
        "new_questions": [
            {
                "question_id": "q2",
                "question": "Why did the input snapshot differ?",
                "actionable": True,
            }
        ],
        "map_unlocks": ["room_b"],
        "end_reason": "all_eligible_actors_resolved",
    }

    game = apply_round_resolution(game, request, resolution)

    assert game.mysteries["q1"]["status"] == "paid_or_transformed"
    assert game.mysteries["q2"]["status"] == "open"
    assert "room_b" in game.map_state["unlocked"]
    assert game.rounds[-1]["material_delta_score"] == 4
