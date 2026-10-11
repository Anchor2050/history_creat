import unittest

from narrative.longform import career_six_2035 as base
from narrative.longform.career_six_finance_housing_v4 import (
    _evaluate_offer_v4,
    _finance_ledger,
    _initial_housing,
    _transfer_up_to,
    simulate_career_six_finance_housing,
)
from narrative.longform.career_six_household_city_v3 import _build_households


class CareerSixFinanceHousingV4Tests(unittest.TestCase):
    def test_ledger_starts_with_user_supplied_cash_and_explicit_pools(self):
        design = base.load_career_six_design()
        ledger = _finance_ledger(design)
        for actor_id, row in design["actors"].items():
            self.assertEqual(ledger.state["accounts"][actor_id], row["cash"])
        self.assertIn("external:salary_pool", ledger.state["accounts"])
        self.assertIn("external:housing_sink", ledger.state["accounts"])
        self.assertIn("external:care_sink", ledger.state["accounts"])

    def test_spending_never_pushes_cash_below_zero(self):
        design = base.load_career_six_design()
        ledger = _finance_ledger(design)
        actor_id = "luo_cheng"
        available = ledger.state["accounts"][actor_id]
        result = _transfer_up_to(
            ledger,
            "test-overlarge-spend",
            actor_id,
            "external:living_sink",
            available + 10000,
            "test partial spend",
        )
        self.assertEqual(result["paid"], available)
        self.assertEqual(result["unmet"], 10000)
        self.assertEqual(ledger.state["accounts"][actor_id], 0)

    def test_existing_home_can_make_distant_reentry_less_feasible(self):
        design = base.load_career_six_design()
        import random
        household = _build_households(design, random.Random(2))["zhou_ye"]
        actor = {"family_care_load": .18}
        housing = _initial_housing()
        housing["zhou_ye"].update({
            "tenure": "owned_mortgage",
            "property_city": "home_prefecture",
            "monthly_mortgage": 2600,
            "lock_in": .80,
        })
        offer = {
            "monthly_gross": 12000.0,
            "housing_monthly": 4600.0,
            "commute_hours_daily": 1.0,
            "family_distance": 3.0,
            "opportunity_density": .90,
            "welfare_continuity": .82,
            "contract_security": .72,
            "flexibility": .60,
        }
        evaluation = _evaluate_offer_v4(
            "zhou_ye", actor, household, housing, offer
        )
        self.assertEqual(evaluation["carry_cost_from_existing_property"], 2600)
        self.assertGreater(evaluation["lock_penalty"], 0)
        self.assertLessEqual(evaluation["score"], evaluation["pre_housing_lock_score"])

    def test_full_run_conserves_total_money_inside_ledger(self):
        run = simulate_career_six_finance_housing(seed=7)
        ledger = run["ledger"]
        self.assertEqual(
            sum(ledger["accounts"].values()),
            sum(ledger["initial_accounts"].values()),
        )
        for actor_id in base.NEW_ACTORS:
            self.assertGreaterEqual(ledger["accounts"][actor_id], 0)

    def test_full_horizon_contains_monthly_finance_rows(self):
        run = simulate_career_six_finance_housing(seed=11)
        self.assertEqual([x["year"] for x in run["annual_snapshots"]], list(range(2026, 2036)))
        expected_months = 10 + 9 * 12
        self.assertEqual(len(run["finance_rows"]), expected_months * len(base.NEW_ACTORS))
        self.assertTrue(all("cash_after" in row for row in run["finance_rows"]))

    def test_some_seed_can_generate_home_purchase_without_forcing_it(self):
        purchases = []
        no_purchase_seen = False
        for seed in range(1, 30):
            run = simulate_career_six_finance_housing(seed=seed)
            if run["home_purchases"]:
                purchases.extend(run["home_purchases"])
            else:
                no_purchase_seen = True
            if purchases and no_purchase_seen:
                break
        self.assertTrue(purchases)
        self.assertTrue(no_purchase_seen)

    def test_owned_home_creates_lock_in_state(self):
        found = None
        for seed in range(1, 35):
            run = simulate_career_six_finance_housing(seed=seed)
            owned = {
                actor_id: row for actor_id, row in run["housing"].items()
                if row["tenure"] == "owned_mortgage"
            }
            if owned:
                found = owned
                break
        self.assertIsNotNone(found)
        for row in found.values():
            self.assertGreater(row["owned_equity"], 0)
            self.assertGreater(row["lock_in"], 0)
            self.assertIsNotNone(row["purchase_year"])

    def test_original_character_feedback_survives_financial_layer(self):
        run = simulate_career_six_finance_housing(seed=17)
        self.assertGreater(run["original_core"]["lin_jing"]["time_pressure"], .35)
        self.assertGreater(run["original_core"]["chen_lan"]["time_pressure"], .52)
        self.assertGreater(run["original_core"]["xu_hang"]["time_pressure"], .40)


if __name__ == "__main__":
    unittest.main()
