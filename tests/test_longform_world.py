import json
import unittest
from pathlib import Path

from narrative.longform.scenarios import compile_beijing
from narrative.longform.world import World, WorldError


ROOT = Path(__file__).resolve().parents[1]


def design():
    with open(ROOT / 'docs' / 'scenarios' / 'beijing-doctoral-initial-v1.json', encoding='utf-8') as handle:
        return json.load(handle)


class LongformWorldTests(unittest.TestCase):
    def world(self):
        return World(compile_beijing(design()))

    def test_compiler_keeps_people_and_makes_money_traceable(self):
        world = self.world(); state = world.snapshot()
        self.assertEqual(len(state['actors']), 8)
        self.assertEqual(len(state['organizations']), 3)
        self.assertEqual(state['ledger']['accounts']['chen_lan'], 14600)
        self.assertEqual(state['ledger']['payments']['contract:old_delivery:payment']['amount'], 3200)
        self.assertEqual(state['artifacts']['chen_thesis']['review_status'], 'not_reviewed')

    def test_added_work_requires_assignee_confirmation(self):
        world = self.world()
        offer = world.offer_task('offer-1', 'zhao_ke', 'chen_lan', 'paid addition', 8,
                                 permission='request_paid_addition', paid_amount=1200)
        self.assertEqual(offer['status'], 'offered')
        self.assertNotIn('offer-1', world.snapshot()['tasks'])
        world.respond_task('reply-1', 'offer-1', 'chen_lan', True)
        self.assertEqual(world.snapshot()['tasks']['offer-1']['status'], 'accepted')

    def test_declining_added_work_creates_no_obligation(self):
        world = self.world()
        world.offer_task('offer-2', 'zhao_ke', 'chen_lan', 'extra unpaid request', 5,
                         permission='request_paid_addition')
        world.respond_task('reply-2', 'offer-2', 'chen_lan', False)
        self.assertNotIn('offer-2', world.snapshot()['tasks'])

    def test_permission_is_enforced(self):
        world = self.world(); before = world.snapshot()
        with self.assertRaises(WorldError):
            world.offer_task('bad', 'xu_hang', 'chen_lan', 'order work', 3,
                             permission='assign_own_project_work')
        self.assertEqual(world.snapshot(), before)

    def test_review_verify_submit_are_separate(self):
        world = self.world()
        world.offer_task('thesis-task', 'wu_cheng', 'chen_lan', 'finish thesis', 4,
                         permission='assign_own_project_work')
        world.respond_task('accept-thesis', 'thesis-task', 'chen_lan', True)
        world.attach_artifact('deliver-thesis', 'thesis-task', 'chen_lan', 'chen_thesis')
        with self.assertRaises(WorldError):
            world.submit_artifact('submit-early', 'chen_lan', 'chen_thesis')
        world.review_artifact('review-thesis', 'wu_cheng', 'chen_thesis', 'review_chen_thesis', 'approve', 'ready')
        with self.assertRaises(WorldError):
            world.submit_artifact('submit-unverified', 'chen_lan', 'chen_thesis')
        world.verify_artifact('verify-thesis', 'sun_jie', 'chen_thesis', 'check_documents')
        world.submit_artifact('submit-thesis', 'chen_lan', 'chen_thesis')
        self.assertEqual(world.snapshot()['artifacts']['chen_thesis']['submission_status'], 'submitted')

    def test_task_booking_uses_assignees_capacity(self):
        world = self.world()
        world.offer_task('o', 'wu_cheng', 'chen_lan', 'analysis', 4, permission='assign_own_project_work')
        world.respond_task('r', 'o', 'chen_lan', True)
        world.reserve_task_time('book', 'o', [
            {'actor': 'chen_lan', 'start': '2026-03-02T09:00', 'end': '2026-03-02T13:00'}])
        with self.assertRaises(WorldError):
            world.reserve_task_time('wrong-person', 'o', [
                {'actor': 'lin_jing', 'start': '2026-03-03T09:00', 'end': '2026-03-03T10:00'}])

    def test_old_receivable_payment_does_not_depend_on_new_contract(self):
        world = self.world()
        world.advance('2026-03-14')
        state = world.snapshot()
        self.assertEqual(state['ledger']['payments']['contract:old_delivery:payment']['status'], 'paid')
        self.assertEqual(state['ledger']['accounts']['chen_lan'], 17800)

    def test_housing_rules_remain_distinct(self):
        state = self.world().snapshot()
        self.assertFalse(state['household']['chen_transition_housing_approved'])
        self.assertTrue(state['household']['lin_next_year_renewal_eligible'])

    def test_help_does_not_change_romantic_consent(self):
        world = self.world()
        relation = next(r for r in world.snapshot()['relationships'] if r.get('kind') == 'former_same_group')
        self.assertFalse(relation['accepted_future_relationship'])
        self.assertFalse(relation['past_help_creates_romantic_entitlement'])


if __name__ == '__main__':
    unittest.main()
