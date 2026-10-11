import pytest

from narrative.longform.storybox_behavior_v11 import (
    build_behavior_task,
    validate_behavior_result,
)
from narrative.longform.storybox_cognition_protocol_v11 import CognitionProtocolError
from narrative.longform.storybox_personal_v11 import (
    build_personal_task,
    validate_personal_result,
)
from narrative.longform.storybox_storyteller_v11 import (
    build_storyteller_task,
    compute_history_thickness,
    validate_storyteller_result,
)


def test_personal_requires_evidence_and_cannot_write_hard_world():
    task = build_personal_task(
        "actor_a",
        [{"ref": "e1", "at": "2028-01-01", "kind": "social_event", "content": "worked late"}],
        as_of="2028-01-31",
    )
    result = {
        "task_id": task["task_id"],
        "kind": "personal_reflection",
        "actor_id": "actor_a",
        "fields": {
            "current_concerns": [{"text": "protecting time matters", "evidence_refs": ["e1"], "confidence": "medium"}],
            "private_goals": [], "unresolved_tensions": [], "routine_preferences": [],
            "interpretations": [], "attention_priorities": [],
        },
        "continuity": [],
        "unknowns": [],
        "evidence_refs": ["e1"],
        "hard_world_writeback": [],
    }
    checked = validate_personal_result(task, result, backend="chatgpt_product_conversation")
    assert checked["status"] == "inferred_personal_candidate_noncanonical"

    result["hard_world_writeback"] = [{"job": "invented"}]
    with pytest.raises(CognitionProtocolError):
        validate_personal_result(task, result, backend="chatgpt_product_conversation")


def test_abnormal_requires_trigger_and_does_not_expand_feasible_actions():
    task = build_behavior_task(
        task_id="behavior:a:1",
        actor_id="a",
        visible_state={"time_pressure": "high"},
        retrieved_memories=[{"ref": "e1", "content": "usually accepts extra work"}],
        personal_state={},
        feasible_actions=[{"action_id": "accept"}, {"action_id": "decline"}],
        evidence_refs=["e1"],
    )
    result = {
        "task_id": task["task_id"], "kind": "behavior_decision", "actor_id": "a",
        "mode": "abnormal", "chosen_action_id": "decline",
        "baseline_expected_action": "accept extra work",
        "deviation": "declines this request",
        "trigger_type": "pressure_accumulation", "trigger_refs": ["e1"],
        "reason": "time pressure makes a boundary-setting deviation plausible",
        "constraint_check": {"feasible": True, "notes": "declining requires no new resource"},
        "evidence_refs": ["e1"],
    }
    checked = validate_behavior_result(task, result, backend="chatgpt_product_conversation")
    assert checked["mode"] == "abnormal"

    bad = dict(result, chosen_action_id="invented_action")
    with pytest.raises(CognitionProtocolError):
        validate_behavior_result(task, bad, backend="chatgpt_product_conversation")


def test_abnormal_budget_prevents_plot_inflation():
    task = build_behavior_task(
        task_id="behavior:a:2", actor_id="a", visible_state={}, retrieved_memories=[],
        personal_state={}, feasible_actions=[{"action_id": "stay"}, {"action_id": "leave"}],
        evidence_refs=["e2"], abnormal_used_in_period=1, abnormal_budget=1,
    )
    result = {
        "task_id": task["task_id"], "kind": "behavior_decision", "actor_id": "a",
        "mode": "abnormal", "chosen_action_id": "leave",
        "baseline_expected_action": "stay", "deviation": "leaves early",
        "trigger_type": "exhaustion", "trigger_refs": ["e2"], "reason": "tired",
        "constraint_check": {"feasible": True, "notes": "can leave"}, "evidence_refs": ["e2"],
    }
    with pytest.raises(CognitionProtocolError):
        validate_behavior_result(task, result, backend="chatgpt_product_conversation")


def test_storyteller_is_read_only_and_traceable():
    batch = {
        "batch_id": "b1",
        "windows": [{"packet_id": "w1"}],
        "events": [
            {"event_id": "e1", "at": "2027-01-01", "speaker": "a", "listener": "b", "act": "check_in", "content": "hello"},
            {"event_id": "e2", "at": "2028-01-01", "speaker": "a", "listener": "b", "act": "share_experience", "content": "later"},
        ],
        "hard_world_candidate_updates": [{"candidate_id": "c1", "result": "rejected_noncanonical"}],
    }
    diagnostic = compute_history_thickness([batch], actor_ids=["a", "b"])
    assert diagnostic["event_count"] == 2
    task = build_storyteller_task(task_id="story:1", batches=[batch], actor_ids=["a", "b"])
    result = {
        "task_id": task["task_id"], "kind": "storyteller_analysis",
        "history_thickness_comment": "still developing",
        "recurring_conflicts": [{"label": "continuity", "interpretation": "the same pair changes over time", "evidence_refs": ["e1", "e2"]}],
        "causal_chains": [], "protagonist_candidates": [], "scene_clusters": [],
        "underrepresented_lives": [], "competing_interpretations": [],
        "recommendation": "continue_history", "evidence_refs": ["e1", "e2"],
        "hard_world_writeback": [],
    }
    checked = validate_storyteller_result(task, result, backend="chatgpt_product_conversation")
    assert checked["status"] == "read_only_storyteller_analysis_noncanonical"

    result["hard_world_writeback"] = [{"invent": "plot"}]
    with pytest.raises(CognitionProtocolError):
        validate_storyteller_result(task, result, backend="chatgpt_product_conversation")
