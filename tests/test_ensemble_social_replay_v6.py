import unittest

from narrative.longform.ensemble_social_replay_v6 import (
    ENSEMBLE_ACTORS,
    PERSONAL_SCENES,
    load_social_design,
    simulate_ensemble_social_replay,
    summarize_ensemble_structure,
)


class EnsembleSocialReplayV6Tests(unittest.TestCase):
    def test_fourteen_people_are_one_ensemble_without_all_to_all_seed(self):
        design = load_social_design()
        self.assertEqual(tuple(design["main_actors"]), ENSEMBLE_ACTORS)
        self.assertEqual(len(ENSEMBLE_ACTORS), 14)
        self.assertLess(len(design["initial_ties"]), 14 * 13 // 2)
        self.assertEqual(set(PERSONAL_SCENES), set(ENSEMBLE_ACTORS))

    def test_core_relationship_layers_are_preserved(self):
        design = load_social_design()
        kinds = {
            frozenset((row["a"], row["b"])): row["kind"]
            for row in design["initial_ties"]
        }
        self.assertEqual(kinds[frozenset(("lin_jing", "chen_lan"))], "roommate")
        self.assertEqual(kinds[frozenset(("chen_lan", "xu_hang"))], "former_same_group")
        self.assertEqual(kinds[frozenset(("zhou_ye", "gao_yuan"))], "same_class")
        self.assertEqual(kinds[frozenset(("tang_yu", "song_nan"))], "same_class")

    def test_every_actor_has_personal_scene_pulses_across_2026_2035(self):
        run = simulate_ensemble_social_replay(seed=7)
        pulses = run["personal_scene_pulses"]
        self.assertEqual(len(pulses), 14 * 10)
        by_actor = {
            actor_id: [row for row in pulses if row["actor"] == actor_id]
            for actor_id in ENSEMBLE_ACTORS
        }
        self.assertTrue(all(len(rows) == 10 for rows in by_actor.values()))
        self.assertTrue(all({row["year"] for row in rows} == set(range(2026, 2036)) for rows in by_actor.values()))

    def test_micro_windows_carry_reverie_and_hard_world_contracts(self):
        run = simulate_ensemble_social_replay(seed=11)
        self.assertTrue(run["micro_replay_packets"])
        for packet in run["micro_replay_packets"]:
            self.assertGreaterEqual(len(packet["participants"]), 2)
            self.assertTrue(packet["reverie_contract"]["use_existing_persona_cognition"])
            self.assertTrue(packet["reverie_contract"]["no_unearned_knowledge"])
            self.assertTrue(packet["reverie_contract"]["remote_chat_must_not_teleport"])
            self.assertEqual(set(packet["participants"]), set(packet["hard_constraints"]))
            self.assertEqual(set(packet["participants"]), set(packet["persona_seeds"]))
            self.assertEqual(set(packet["participants"]), set(packet["memory_seeds"]))

    def test_remote_windows_are_marked_as_nonphysical_locations(self):
        run = simulate_ensemble_social_replay(seed=23)
        remote = {
            "phone", "wechat_private", "wechat_group", "email", "video_call"
        }
        rows = [p for p in run["micro_replay_packets"] if p["mode"] in remote]
        self.assertTrue(rows)
        self.assertTrue(all(p["location"].startswith("digital:") for p in rows))

    def test_relationships_can_grow_through_introduction(self):
        run = simulate_ensemble_social_replay(seed=7)
        introduced = [
            row for row in run["social_graph"]["ties"]
            if row["origin"] == "event_introduction"
        ]
        self.assertTrue(introduced)
        for row in introduced:
            self.assertTrue(row["shared_events"])
            self.assertEqual(row["kind"], "introduced_acquaintance")
            self.assertIn(row["a"], ENSEMBLE_ACTORS)
            self.assertIn(row["b"], ENSEMBLE_ACTORS)

    def test_no_actor_is_only_a_functional_support_node_in_reference_seed(self):
        run = simulate_ensemble_social_replay(seed=7)
        summary = summarize_ensemble_structure(run)
        self.assertEqual(summary["actors_without_personal_scene"], [])
        self.assertEqual(summary["actors_without_personal_pulse"], [])
        self.assertEqual(summary["actors_without_micro_scene"], [])


if __name__ == "__main__":
    unittest.main()
