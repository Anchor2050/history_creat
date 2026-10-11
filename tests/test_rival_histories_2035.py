from narrative.longform.rival_histories_2035_v1 import (
    ALPHA_QUIET_RUPTURE,
    BETA_EXERCISED_MOBILITY,
    ledger,
    validate,
)


def test_rival_histories_pass_structural_validation():
    for history in (ALPHA_QUIET_RUPTURE, BETA_EXERCISED_MOBILITY):
        checks = validate(history)
        assert checks
        assert all(checks.values()), checks


def test_alpha_preserves_unrepaired_relationship_cost():
    by_id = {e["id"]: e for e in ALPHA_QUIET_RUPTURE}
    assert by_id["a33_1"]["delta"]["trust"] < 0
    assert by_id["a35_3"]["delta"]["trust"] <= 0
    assert "和解" in by_id["a35_3"]["cost"] or "重逢" in by_id["a35_3"]["cost"]


def test_beta_mobility_is_bundle_exchange_not_free_gain():
    by_id = {e["id"]: e for e in BETA_EXERCISED_MOBILITY}
    move = by_id["b32_1"]["delta"]
    assert move["mobility"] > 0
    assert move["bargaining_power"] > 0
    assert move["welfare_continuity"] < 0
    assert move["care_robustness"] < 0


def test_ordinal_ledgers_do_not_create_scalar_success():
    for history in (ALPHA_QUIET_RUPTURE, BETA_EXERCISED_MOBILITY):
        snapshots = ledger(history)
        assert len(snapshots) == len(history)
        for snapshot in snapshots:
            for state in snapshot["states"].values():
                assert "success" not in state
                assert "score" not in state
