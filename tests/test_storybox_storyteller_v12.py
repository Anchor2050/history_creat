from narrative.longform.storybox_storyteller_v12 import (
    build_evidence_graph,
    candidate_lifecycles,
    compute_history_thickness_v12,
    unresolved_threads,
)


def _batches():
    return [
        {
            "batch_id": "b1",
            "windows": [{"packet_id": "w1"}],
            "events": [
                {
                    "event_id": "e1",
                    "at": "2028-01-01",
                    "speaker": "a",
                    "listener": "b",
                    "event_kind": "checkin",
                    "act": "check_in",
                    "content": "hello",
                }
            ],
            "new_hard_world_candidates": [
                {
                    "candidate_id": "c1",
                    "created_at": "2028-01-02",
                    "beneficiary": "a",
                    "status": "pending",
                },
                {
                    "candidate_id": "c2",
                    "created_at": "2028-01-03",
                    "beneficiary": "b",
                    "status": "pending",
                },
            ],
        },
        {
            "batch_id": "b2",
            "windows": [{"packet_id": "w2"}],
            "events": [
                {
                    "event_id": "e2",
                    "at": "2029-02-01",
                    "speaker": "a",
                    "listener": "b",
                    "event_kind": "followup",
                    "act": "share_experience",
                    "content": "followup",
                }
            ],
            "hard_world_candidate_updates": [
                {
                    "candidate_id": "c1",
                    "checked_at": "2029-02-02",
                    "result": "closed_failed",
                }
            ],
            "actor_state_evidence": [
                {
                    "at": "2029-02-03",
                    "actor": "a",
                    "dimension": "work",
                    "evidence": "state evidence",
                }
            ],
        },
    ]


def test_evidence_graph_links_candidate_lifecycle_without_inventing_causality():
    graph = build_evidence_graph(_batches())
    lifecycle_edges = [row for row in graph["edges"] if row["kind"] == "candidate_lifecycle"]
    chronology_edges = [row for row in graph["edges"] if row["kind"] == "actor_chronology"]
    assert len(lifecycle_edges) == 1
    assert lifecycle_edges[0]["candidate_id"] == "c1"
    assert chronology_edges
    assert not any(row["kind"] == "causes" for row in graph["edges"])


def test_candidate_lifecycle_distinguishes_closed_and_open_threads():
    graph = build_evidence_graph(_batches())
    rows = {row["candidate_id"]: row for row in candidate_lifecycles(graph)}
    assert rows["c1"]["outcome"] == "closed_or_failed"
    assert rows["c2"]["outcome"] == "open_or_ambiguous"
    open_ids = {row["thread_id"] for row in unresolved_threads(graph)}
    assert "c2" in open_ids
    assert "c1" not in open_ids


def test_history_thickness_is_diagnostic_only_and_preserves_actor_coverage():
    result = compute_history_thickness_v12(_batches(), actor_ids=["a", "b", "c"])
    assert result["window_count"] == 2
    assert result["social_event_count"] == 2
    assert result["readiness"] in {"thin", "developing", "substantial"}
    coverage = {row["actor_id"]: row for row in result["viewpoint_coverage"]}
    assert coverage["a"]["evidence_count"] > 0
    assert coverage["b"]["evidence_count"] > 0
    assert coverage["c"]["evidence_count"] == 0
    assert "never an aesthetic score" in result["note"]
