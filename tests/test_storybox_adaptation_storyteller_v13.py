from narrative.longform.storybox_adaptation_storyteller_v13 import (
    AdaptationStorytellerError,
    build_scene_probe_task,
    protagonist_weight_check,
    scene_priority,
    select_balanced_reservoir,
    validate_scene_card,
)


def _card(scene_id="s1", part=1, viewpoint="zhou_ye"):
    return {
        "scene_id": scene_id,
        "part": part,
        "year": "2026",
        "label": "test",
        "primary_viewpoint": viewpoint,
        "participants": [viewpoint, "xu_hang"],
        "evidence_refs": ["batch1:e01"],
        "surface_action": "ask for advice",
        "dramatic_question": "can reliability become visible?",
        "inner_conflict": "responsibility versus need to be needed",
        "power_structure": "doctoral candidate seeking legible value",
        "hero_stage_function": "call",
        "scene_tier": "must_keep",
        "scores": {
            "historical_leverage": 5,
            "character_revelation": 5,
            "relationship_pressure": 2,
            "material_concreteness": 3,
            "power_visibility": 3,
            "ordinary_life_counterpoint": 1,
            "visual_or_sensory_potential": 2,
        },
        "active_archetype_roles": [{"actor":"xu_hang","role":"mentor"}],
        "adaptation_hypotheses": {"declared_as_history": False},
        "world_writeback": False,
    }


def test_scene_card_is_read_only_and_scored():
    card = validate_scene_card(_card())
    assert card["world_writeback"] is False
    assert scene_priority(card) > 0


def test_unknown_evidence_is_rejected_when_reference_set_supplied():
    try:
        validate_scene_card(_card(), known_evidence_refs={"different:ref"})
    except AdaptationStorytellerError:
        pass
    else:
        raise AssertionError("unknown evidence ref should fail")


def test_probe_task_never_writes_history():
    task = build_scene_probe_task(
        _card(),
        character_design_refs=["docs/adaptation/character-psychology-bible-v1.md"],
        style_guardrail_ref="docs/adaptation/literary-style-guardrails-v1.md",
    )
    assert task["world_writeback"] is False
    assert task["task_kind"] == "adaptation_scene_probe_noncanonical"


def test_balanced_selection_and_viewpoint_audit():
    cards = []
    for part in range(1, 5):
        for i in range(6):
            actor = ["zhou_ye", "gao_yuan", "luo_cheng", "tang_yu", "he_xin", "song_nan"][i]
            cards.append(_card(scene_id=f"p{part}-{i}", part=part, viewpoint=actor))
    selected = select_balanced_reservoir(cards, limit=24, min_per_part=5)
    assert len(selected) == 24
    assert {row["part"] for row in selected} == {1, 2, 3, 4}
    audit = protagonist_weight_check(selected, ["zhou_ye", "gao_yuan", "luo_cheng", "tang_yu", "he_xin", "song_nan"])
    assert all(v > 0 for v in audit["viewpoint_scene_counts"].values())
