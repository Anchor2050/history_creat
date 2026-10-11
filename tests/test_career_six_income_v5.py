import random
import unittest

from narrative.longform import career_six_2035 as base
from narrative.longform.career_six_income_v5 import (
    _draw_income_profiles,
    _finance_ledger_v5,
    load_income_priors,
    simulate_career_six_income,
    summarize_income_sensitivity,
)


class CareerSixIncomeV5Tests(unittest.TestCase):
    def test_income_priors_do_not_encode_gender_or_sibling_support_rule(self):
        priors = load_income_priors()
        rule = priors["family_support_monthly"]["rule"]
        self.assertIn("六人使用同一开放区间", rule)
        self.assertIn("不决定金额", rule)

    def test_seed_draws_explicit_income_profiles_for_all_six(self):
        design = base.load_career_six_design()
        priors = load_income_priors()
        profiles = _draw_income_profiles(design, priors, random.Random(4))
        self.assertEqual(set(profiles), set(base.NEW_ACTORS))
        for actor_id, row in profiles.items():
            self.assertGreaterEqual(row["doctoral_stipend_monthly"], priors["doctoral_stipend_monthly"]["min"])
            self.assertLessEqual(row["doctoral_stipend_monthly"], priors["doctoral_stipend_monthly"]["max"])
            self.assertGreaterEqual(row["family_support_monthly"], 0)
            self.assertGreater(row["employment_net_pay_share"], 0)

    def test_income_profiles_change_across_seeds(self):
        design = base.load_career_six_design()
        priors = load_income_priors()
        a = _draw_income_profiles(design, priors, random.Random(1))
        b = _draw_income_profiles(design, priors, random.Random(2))
        self.assertNotEqual(a, b)

    def test_v5_ledger_has_explicit_preemployment_income_pools(self):
        design = base.load_career_six_design()
        ledger = _finance_ledger_v5(design)
        for account in (
            "external:stipend_pool",
            "external:family_support_pool",
            "external:temporary_work_pool",
            "external:search_support_pool",
        ):
            self.assertIn(account, ledger.state["accounts"])

    def test_doctoral_months_can_receive_stipend_before_first_job(self):
        run = simulate_career_six_income(seed=5)
        march = [
            row for row in run["finance_rows"]
            if row["date"].startswith("2026-03")
        ]
        self.assertEqual(len(march), len(base.NEW_ACTORS))
        self.assertTrue(all(row["doctoral_stipend"] > 0 for row in march))

    def test_money_conservation_survives_income_layer(self):
        run = simulate_career_six_income(seed=7)
        ledger = run["ledger"]
        self.assertEqual(
            sum(ledger["accounts"].values()),
            sum(ledger["initial_accounts"].values()),
        )
        self.assertTrue(all(ledger["accounts"][actor_id] >= 0 for actor_id in base.NEW_ACTORS))

    def test_income_profiles_are_retained_for_audit(self):
        run = simulate_career_six_income(seed=9)
        self.assertEqual(set(run["income_profiles"]), set(base.NEW_ACTORS))
        self.assertIn("收入先验必须随seed变化并可在输出中检查。", run["income_prior_rules"])
        self.assertIn("不代表真实博士津贴", run["engineering_prior_notice"])

    def test_sensitivity_summary_does_not_select_a_canonical_world(self):
        summary = summarize_income_sensitivity(seeds=(1, 2, 3))
        self.assertEqual(summary["status"], "sensitivity_diagnostic_noncanonical")
        self.assertEqual(len(summary["runs"]), 3)
        self.assertEqual(set(summary["purchase_counts"]), set(base.NEW_ACTORS))
        self.assertEqual(set(summary["destination_variety"]), set(base.NEW_ACTORS))


if __name__ == "__main__":
    unittest.main()
