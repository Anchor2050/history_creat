import unittest
from copy import deepcopy
from narrative.core import World, InvalidAction
from test_core import scenario


def rich():
    s = scenario()
    s['facts']['secret'] = {'text': 'Bridge unsafe', 'false_text': 'Bridge safe', 'truth': True, 'location': 'yard'}
    s['actors']['b']['claims'] = {'secret': {'value': False, 'source': 'rumor', 'event': None}}
    s['actors']['a']['resources'] = {'energy': 2}
    s['actors']['b']['goals'] = [{'id': 'aid', 'description': 'Get aid', 'condition': {'kind': 'resource', 'resource': 'food', 'at_least': 2}}]
    s['organizations'] = {'guild': {'members': {'a': 'chief', 'b': 'member'}, 'permissions': {'allocate': ['chief'], 'enact': ['chief']}, 'resources': {'food': 3}, 'policies': {'ration': 'equal'}, 'policy_options': {'ration': ['equal', 'need']}}}
    s['rules'] = {'repair': {'description': 'Repair gate using energy', 'location': 'hall', 'cost': {'energy': 1}, 'effects': {'flags': {'gate_open': True}}}}
    return s


class WorldV2Tests(unittest.TestCase):
    def test_false_belief_and_investigation(self):
        w = World(rich())
        self.assertIn('Bridge safe', str(w.view('b')['beliefs']))
        self.assertNotIn('truth', str(w.view('b')))
        w.act({'actor': 'b', 'kind': 'move', 'target': 'yard'})
        w.act({'actor': 'b', 'kind': 'investigate', 'fact': 'secret'})
        self.assertTrue(w.state['actors']['b']['claims']['secret']['value'])
        self.assertIn('Bridge unsafe', str(w.view('b')['beliefs']))

    def test_delayed_message_and_causal_dependency(self):
        w = World(rich())
        sent = w.act({'actor': 'a', 'kind': 'send', 'target': 'c', 'fact': 'secret', 'delay': 2})
        self.assertNotIn('secret', w.view('c')['beliefs'])
        w.act({'actor': 'b', 'kind': 'wait'})
        arrival = w.act({'actor': 'b', 'kind': 'wait'})
        self.assertIn('secret', w.view('c')['beliefs'])
        self.assertIn(sent['id'], arrival['dependencies'])
        self.assertNotIn('a', w.view('c')['nearby'])

    def test_organization_permissions_conservation_and_goal(self):
        w = World(rich())
        bad = {'actor': 'b', 'kind': 'allocate', 'org': 'guild', 'resource': 'food', 'amount': 2, 'target': 'b'}
        before = w.snapshot()
        with self.assertRaises(InvalidAction):
            w.act(bad)
        self.assertEqual(w.snapshot(), before)
        w.act(dict(bad, actor='a'))
        self.assertEqual(w.state['organizations']['guild']['resources']['food'], 1)
        self.assertEqual(w.state['actors']['b']['resources']['food'], 2)
        self.assertEqual(w.state['actors']['b']['goals'][0]['status'], 'achieved')
        with self.assertRaises(InvalidAction):
            w.act(dict(bad, actor='a'))

    def test_rules_and_automatic_dependencies(self):
        w = World(rich())
        first = w.act({'actor': 'a', 'kind': 'perform', 'rule': 'repair'})
        second = w.act({'actor': 'a', 'kind': 'perform', 'rule': 'repair'})
        self.assertTrue(w.state['flags']['gate_open'])
        self.assertEqual(w.state['actors']['a']['resources']['energy'], 0)
        self.assertIn(first['id'], second['dependencies'])
        with self.assertRaises(InvalidAction):
            w.act({'actor': 'a', 'kind': 'perform', 'rule': 'repair'})

    def test_broken_promise_changes_trust_not_global_character(self):
        w = World(rich())
        traits = w.state['actors']['b']['traits']
        w.act({'actor': 'a', 'kind': 'promise', 'target': 'b', 'item': 'coin', 'due_in': 1})
        w.act({'actor': 'c', 'kind': 'wait'})
        self.assertLess(w.state['actors']['b']['relationships']['a']['trust'], 0)
        self.assertEqual(w.state['actors']['b']['traits'], traits)
        self.assertTrue(w.view('b')['experiences'])

    def test_policy_and_branch(self):
        w = World(rich())
        w.act({'actor': 'a', 'kind': 'enact', 'org': 'guild', 'policy': 'ration', 'value': 'need'})
        other = w.branch('alternative')
        other.act({'actor': 'a', 'kind': 'wait'})
        self.assertEqual(len(w.events), 1)
        self.assertEqual(other.snapshot()['branch']['parent_tick'], 1)
        self.assertEqual(World.restore(other.snapshot()).snapshot(), other.snapshot())

    def test_reflection_cannot_cite_unknown_history(self):
        w = World(rich())
        event = w.act({'actor': 'a', 'kind': 'wait'})
        with self.assertRaises(InvalidAction):
            w.reflect('c', 'I learned something', [event['id']])
        w.reflect('a', 'I should act sooner', [event['id']])
        self.assertIn('act sooner', str(w.view('a')['self']['reflections']))

    def test_actions_menu_contains_no_world_truth(self):
        w = World(rich())
        menu = w.actions('b')
        self.assertTrue(any(a['kind'] == 'tell' for a in menu))
        self.assertFalse(any(a['kind'] == 'allocate' for a in menu))
        self.assertNotIn('truth', str(menu))

    def test_unknown_rule_effect_rejected_on_load(self):
        s = rich()
        s['rules']['repair']['effects']['anything'] = True
        with self.assertRaises(ValueError):
            World(s)
