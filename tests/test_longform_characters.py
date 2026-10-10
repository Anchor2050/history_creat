import json
import unittest
from pathlib import Path

from narrative.longform.characters import Characters, CharacterError
from narrative.longform.scenarios import compile_beijing


ROOT = Path(__file__).resolve().parents[1]


def actors():
    with open(ROOT / 'docs' / 'scenarios' / 'beijing-doctoral-initial-v1.json', encoding='utf-8') as handle:
        return compile_beijing(json.load(handle))['actors']


class LongformCharacterTests(unittest.TestCase):
    def chars(self):
        return Characters(actors())

    def test_private_fact_stays_local(self):
        chars = self.chars()
        chen = chars.visible_context('chen_lan')
        lin = chars.visible_context('lin_jing')
        self.assertIn('cash_balance', chen['private'])
        self.assertNotIn('cash_balance', lin['known'])
        self.assertNotIn('cash_balance', lin['private'])

    def test_unknown_confession_does_not_leak(self):
        chars = self.chars()
        chars.learn('xu_hang', 'private_confession_detail', private=True, source='direct experience')
        self.assertIn('private_confession_detail', chars.visible_context('xu_hang')['private'])
        self.assertNotIn('private_confession_detail', chars.visible_context('chen_lan')['known'])

    def test_plan_revision_requires_seen_experience(self):
        chars = self.chars()
        chars.add_plan('chen_lan', 'finish-thesis', 'finish submission', 2, 10, ['submission_deadline'])
        with self.assertRaises(CharacterError):
            chars.revise_plan('chen_lan', 'finish-thesis', 'delay submission', 5, ['secret_future_event'])
        chars.learn('chen_lan', 'review_failed', source='advisor review')
        chars.revise_plan('chen_lan', 'finish-thesis', 'repair core tables before submission', 12, ['review_failed'])
        self.assertEqual(chars.visible_context('chen_lan')['plans'][0]['priority'], 12)

    def test_commitment_impact_must_reference_existing_commitment(self):
        chars = self.chars()
        chars.add_plan('lin_jing', 'paper', 'revise sampling argument', 2, 8, ['dorm_shared'])
        chars.learn('lin_jing', 'advisor_slot_cancelled')
        with self.assertRaises(CharacterError):
            chars.revise_plan('lin_jing', 'paper', 'reschedule', 9, ['advisor_slot_cancelled'], ['missing'])
        chars.add_commitment('lin_jing', 'roommate-evening', 'keep Thursday evening free', to_actor='chen_lan')
        chars.revise_plan('lin_jing', 'paper', 'reschedule around roommate commitment', 9,
                          ['advisor_slot_cancelled'], ['roommate-evening'])

    def test_reflection_cannot_use_omniscient_evidence(self):
        chars = self.chars()
        with self.assertRaises(CharacterError):
            chars.reflect('lin_jing', 'r1', 'I know Zhao is under client pressure', ['client_pressure'])
        chars.learn('lin_jing', 'zhao_said_client_pressure', source='conversation')
        chars.reflect('lin_jing', 'r1', 'The project manager is under pressure', ['zhao_said_client_pressure'])
        self.assertEqual(len(chars.visible_context('lin_jing')['reflections']), 1)

    def test_trust_is_domain_specific(self):
        chars = self.chars()
        chars.learn('chen_lan', 'xu_helped_with_table', source='observed help')
        chars.update_trust('chen_lan', 'xu_hang', 'research_reliability', 1, 'xu_helped_with_table')
        context = chars.visible_context('chen_lan')
        self.assertEqual(context['trust']['xu_hang:research_reliability'], 1)
        self.assertNotIn('xu_hang:romantic', context['trust'])

    def test_snapshot_restore_roundtrip(self):
        chars = self.chars()
        chars.learn('chen_lan', 'new_fact', private=True)
        restored = Characters.restore(chars.snapshot())
        self.assertEqual(restored.snapshot(), chars.snapshot())


if __name__ == '__main__':
    unittest.main()
