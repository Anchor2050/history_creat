from narrative.longform.storybox_sck_eval_v0 import (
    ActionCheckpoint,
    BeliefCheckpoint,
    CommunicationCheckpoint,
    EpisodeEvaluation,
    aggregate_episodes,
)
from narrative.longform.storybox_sck_v0 import BeliefState


def test_episode_summary_reports_brier_regret_and_leakage():
    episode = EpisodeEvaluation(
        variant_id="belief_planning",
        won=True,
        utility=1.0,
        belief_checkpoints=[
            BeliefCheckpoint(
                step_id="s1",
                belief=BeliefState({"truth": 0.8, "other": 0.2}),
                true_hypothesis="truth",
            )
        ],
        action_checkpoints=[
            ActionCheckpoint(
                step_id="s1",
                chosen_action_id="a",
                action_values={"a": 0.7, "b": 1.0},
            )
        ],
        communication_checkpoints=[
            CommunicationCheckpoint(
                step_id="s1",
                protected_facts=["role"],
                disclosed_facts=["role", "public_fact"],
            )
        ],
    )

    summary = episode.summary()
    assert summary["won"] is True
    assert summary["mean_brier"] is not None
    assert abs(summary["mean_immediate_target_loss_diagnostic"] - 0.3) < 1e-12
    assert summary["information_leakage_count"] == 1


def test_aggregate_keeps_variants_separate():
    episodes = [
        EpisodeEvaluation(variant_id="plain", won=False, utility=0.0),
        EpisodeEvaluation(variant_id="plain", won=True, utility=1.0),
        EpisodeEvaluation(variant_id="belief", won=True, utility=1.0),
    ]

    result = aggregate_episodes(episodes)
    assert result["plain"]["episodes"] == 2
    assert result["plain"]["win_rate"] == 0.5
    assert result["belief"]["win_rate"] == 1.0
