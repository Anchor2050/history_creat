import random
import unittest

from narrative.longform import career_six_2035 as base
from narrative.longform.career_six_household_city_v3 import (
    CITY_BUNDLES,
    _build_households,
    _evaluate_offer,
    _generate_offer,
    simulate_career_six_household_city,
)


class CareerSixHouseholdCityV3Tests(unittest.TestCase):
    def test_fixed_family_structure_becomes_explicit_nodes(self):
        design = base.load_career_six_design()
        households = _build_households(design, random.Random(3))

        for actor_id in ("zhou_ye", "gao_yuan", "luo_cheng"):
            household = households[actor_id]
            self.assertEqual(household["siblings"], [])
            self.assertEqual(
                {x["employment_context"] for x in household["parents"].values()},
                {"dual_income_fixed"},
            )

        for actor_id in ("tang_yu", "he_xin", "song_nan"):
            household = households[actor_id]
            self.assertEqual(len(household["siblings"]), 2)
            self.assertEqual(
                {x["id"] for x in household["siblings"]},
                {f"{actor_id}:older_brother_1", f"{actor_id}:older_brother_2"},
            )

    def test_brothers_are_individual_scenario_nodes_not_one_shared_scalar(self):
        design = base.load_career_six_design()
        a = _build_households(design, random.Random(4))["he_xin"]["siblings"]
        b = _build_households(design, random.Random(9))["he_xin"]["siblings"]
        self.assertEqual(len(a), 2)
        self.assertTrue(all("care_willingness" in x for x in a))
        self.assertTrue(all("partner_child_load" in x for x in a))
        self.assertNotEqual(a, b)

    def test_offer_is_a_bundle_not_a_sector_label(self):
        design = base.load_career_six_design()
        households = _build_households(design, random.Random(5))
        actor = {
            "current_target": "pharmaceutical_industry",
            "family_care_load": .20,
            "cash": 25000.0,
            "preferred_city_shift": None,
        }
        offer = _generate_offer(
            "song_nan", actor, households["song_nan"], random.Random(8), 2028, "first_job"
        )
        for field in (
            "sector", "city", "monthly_gross", "housing_monthly",
            "commute_hours_daily", "welfare_continuity", "opportunity_density",
            "family_distance", "contract_security", "flexibility", "relocation_cost",
        ):
            self.assertIn(field, offer)
        self.assertIn(offer["city"], CITY_BUNDLES)
        self.assertTrue(offer["engineering_prior"])

    def test_same_sector_can_produce_different_city_bundles(self):
        design = base.load_career_six_design()
        household = _build_households(design, random.Random(12))["zhou_ye"]
        actor = {
            "current_target": "state_owned_enterprise",
            "family_care_load": .10,
            "cash": 26000.0,
            "preferred_city_shift": None,
        }
        cities = {
            _generate_offer("zhou_ye", actor, household, random.Random(seed), 2027, "first_job")["city"]
            for seed in range(1, 15)
        }
        self.assertGreaterEqual(len(cities), 2)

    def test_family_gap_can_make_a_won_offer_infeasible(self):
        design = base.load_career_six_design()
        household = _build_households(design, random.Random(1))["zhou_ye"]
        household["unmet_care"] = .55
        household["sibling_substitution"] = 0.0
        actor = {
            "family_care_load": .62,
        }
        offer = {
            "monthly_gross": 10000.0,
            "housing_monthly": 4500.0,
            "commute_hours_daily": 1.0,
            "family_distance": 3.2,
            "opportunity_density": .85,
            "welfare_continuity": .80,
            "contract_security": .80,
            "flexibility": .55,
        }
        evaluation = _evaluate_offer("zhou_ye", actor, household, offer)
        self.assertTrue(evaluation["hard_family_block"])
        self.assertFalse(evaluation["accepted"])

    def test_full_horizon_retains_households_offers_and_old_character_feedback(self):
        run = simulate_career_six_household_city(seed=7)
        self.assertEqual([x["year"] for x in run["annual_snapshots"]], list(range(2026, 2036)))
        self.assertEqual(set(run["households"]), set(base.NEW_ACTORS))
        self.assertGreater(len(run["offers"]), 0)
        self.assertGreater(run["original_core"]["lin_jing"]["time_pressure"], .35)
        self.assertGreater(run["original_core"]["chen_lan"]["time_pressure"], .52)
        self.assertGreater(run["original_core"]["xu_hang"]["time_pressure"], .40)
        self.assertIn("fictional replay priors", run["engineering_prior_notice"])

    def test_multiple_seeds_can_change_bundle_and_2035_destination(self):
        runs = [simulate_career_six_household_city(seed=s) for s in (1, 7, 23)]
        final_states = {
            tuple((run["actors"][aid]["sector"], run["actors"][aid]["city_state"]) for aid in base.NEW_ACTORS)
            for run in runs
        }
        self.assertGreaterEqual(len(final_states), 2)

    def test_offer_rejection_is_separate_from_capacity_block_and_skill_failure(self):
        outcomes = set()
        for seed in range(1, 35):
            run = simulate_career_six_household_city(seed=seed)
            outcomes.update(x["outcome"] for x in run["job_cycles"] + run["reentries"])
            if {"offer_rejected", "capacity_blocked", "qualification_failed"}.issubset(outcomes):
                break
        self.assertTrue({"offer_rejected", "capacity_blocked", "qualification_failed"}.issubset(outcomes))


if __name__ == "__main__":
    unittest.main()
