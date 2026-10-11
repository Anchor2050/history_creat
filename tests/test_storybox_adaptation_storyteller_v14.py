from narrative.longform.storybox_adaptation_storyteller_v14 import (
    NestedStoryError,
    validate_guest_dossier,
    reverse_plausibility_audit,
    validate_substory_card,
    guest_needed,
)


def _guest():
    return {
        "guest_id":"guest:test",
        "display_name":"测试角色",
        "current_role":"bounded project counterpart",
        "current_goal":"finish a deliverable without taking uncontrolled risk",
        "pressure":"deadline and limited authority",
        "virtue":"careful accountability",
        "shadow":"over-controls access when uncertain",
        "power_position":"cross_cutting",
        "information_set":{"knows":["project scope"],"does_not_know":["protagonist private history"]},
        "interaction_mode_with_protagonist":"peer",
        "micro_arc_pattern":"desire_friction_misjudgment_correction",
        "micro_arc_steps":["desire","friction","misjudgment","small correction"],
        "status":"adaptation_only_candidate",
        "historical_world_writeback":False,
    }


def test_guest_requires_adaptation_only_and_micro_arc():
    row = validate_guest_dossier(_guest())
    assert row["historical_world_writeback"] is False
    assert len(row["micro_arc_steps"]) == 4


def test_failed_plausibility_blocks_guest():
    checks = {
        "time_feasible":True,
        "institution_feasible":True,
        "professional_feasible":True,
        "relationship_feasible":True,
        "information_feasible":False,
        "interest_feasible":True,
        "psychology_feasible":True,
        "era_feasible":True,
    }
    result = reverse_plausibility_audit(_guest(), checks)
    assert result["passed"] is False
    assert result["result"] == "revise_or_delete_guest"


def test_substory_must_keep_history_refs():
    card = {
        "substory_id":"sub:test",
        "protagonist":"zhou_ye",
        "time_window":"2034",
        "ordinary_world":"one expert handles exceptions",
        "call":"single point becomes costly",
        "threshold_or_resistance":"delegating judgment",
        "interaction_chain":["training","live case","review"],
        "local_transformation":"partial delegation",
        "residual_cost":"rare cases remain",
        "main_arc_function":"post-return governance",
        "evidence_refs":["2034q3:e03"],
        "historical_world_writeback":False,
    }
    checked = validate_substory_card(card)
    assert checked["evidence_refs"]


def test_guest_created_only_for_real_function_gap():
    result = guest_needed(
        scene_functions=["domain_counterpart", "mentor"],
        existing_participant_functions={"xu_hang":["mentor"]},
    )
    assert result["guest_needed"] is True
    assert result["missing_functions"] == ["domain_counterpart"]
