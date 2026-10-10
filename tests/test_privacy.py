import unittest
from narrative.core import World, InvalidAction
from test_world_v2 import rich


class PrivacyTests(unittest.TestCase):
    def test_candidate_menu_does_not_reveal_targets_private_beliefs(self):
        left = rich()
        right = rich()
        right['actors']['b']['claims']['secret'] = {'value': True, 'source': 'initial', 'event': None}
        self.assertEqual(World(left).actions('a'), World(right).actions('a'))

    def test_allocation_policy_changes_real_options(self):
        s = rich()
        s['organizations']['guild']['allocation_limits'] = {'ration': {'equal': 1, 'need': 3}}
        w = World(s)
        action = {'actor': 'a', 'kind': 'allocate', 'org': 'guild', 'resource': 'food', 'amount': 2, 'target': 'b'}
        with self.assertRaises(InvalidAction):
            w.act(action)
        e = w.act({'actor': 'a', 'kind': 'enact', 'org': 'guild', 'policy': 'ration', 'value': 'need'})
        result = w.act(action)
        self.assertIn(e['id'], result['dependencies'])

    def test_large_stock_does_not_offer_unexecutable_requests(self):
        s = rich()
        s['organizations']['guild']['resources']['food'] = 250
        w = World(s)
        for action in w.actions('b'):
            if action['kind'] == 'request':
                World.restore(w.snapshot()).act(action)
