import unittest

from narrative.longform.career_six_2035 import (
    ALL_EXISTING,
    NEW_ACTORS,
    load_career_six_design,
    simulate_career_six_world,
)


class CareerSix2035Tests(unittest.TestCase):
    def test_fixed_user_constraints_are_preserved(self):
        design = load_career_six_design()
        actors = design["actors"]
        men = [actors[x] for x in ("zhou_ye", "gao_yuan", "luo_cheng")]
        women = [actors[x] for x in ("tang_yu", "he_xin", "song_nan")]

        self.assertTrue(all(x["field"] == "mathematics_probability" for x in men))
        self.assertTrue(all(x["published_papers"] == 0 for x in men))
        self.assertTrue(all(x["only_child"] for x in men))
        self.assertTrue(all(x["parents_employment"] == "dual_income" for x in men))
        self.assertEqual(
            [x["career_target_2026"] for x in men],
            ["state_owned_enterprise", "civil_service", "university_counselor"],
        )

        self.assertTrue(all(x["field"] == "survival_analysis" for x in women))
        self.assertTrue(all(x["sibling_order"] == 3 for x in women))
        self.assertTrue(all(x["older_brothers"] == 2 for x in women))
        self.assertEqual(
            [x["career_target_2026"] for x in women],
            ["university_faculty", "civil_service_or_public_institution", "pharmaceutical_industry"],
        )

    def test_horizon_runs_from_2026_through_2035(self):
        run = simulate_career_six_world(seed=7)
        self.assertEqual(run["start_date"], "2026-03-02")
        self.assertEqual(run["end_date"], "2035-12-31")
        self.assertEqual([x["year"] for x in run["annual_snapshots"]], list(range(2026, 2036)))
        self.assertEqual(set(run["actors"]), set(NEW_ACTORS))

    def test_new_people_interact_with_existing_branch_people(self):
        run = simulate_career_six_world(seed=11)
        touched = {x["existing_actor"] for x in run["interactions"]}
        self.assertTrue({"lin_jing", "chen_lan", "xu_hang"}.issubset(touched))
        self.assertTrue(touched.issubset(set(ALL_EXISTING)))
        self.assertGreater(run["original_core"]["lin_jing"]["public_sector_option"], .20)
        self.assertGreater(run["original_core"]["chen_lan"]["health_data_translation"], .20)
        self.assertGreater(run["original_core"]["xu_hang"]["verification_reputation"], .42)

    def test_family_structure_changes_pressure_without_hard_coding_destiny(self):
        run = simulate_career_six_world(seed=13)
        men = [run["actors"][x] for x in ("zhou_ye", "gao_yuan", "luo_cheng")]
        women = [run["actors"][x] for x in ("tang_yu", "he_xin", "song_nan")]
        self.assertTrue(all(.72 <= x["family_care_share"] <= .98 for x in men))
        self.assertTrue(all(.22 <= x["family_care_share"] <= .68 for x in women))
        self.assertTrue(all(x["family_care_load"] >= 0 for x in men + women))
        self.assertIn("家庭结构只改变约束、资源与照护协商，不直接决定人物选择或命运。", run["fixed_design_rules"])

    def test_topology_contains_old_and_new_actors(self):
        run = simulate_career_six_world(seed=17)
        status = run["topology"]["actor_status"]
        for actor_id in NEW_ACTORS + ALL_EXISTING:
            self.assertIn(actor_id, status)


if __name__ == "__main__":
    unittest.main()
