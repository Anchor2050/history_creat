import unittest
from copy import deepcopy
from narrative.core import World, InvalidAction


def scenario():
    return {'locations': ['hall', 'yard'], 'routes': [['hall', 'yard']],
            'actors': {'a': {'location': 'hall', 'traits': 'loyal', 'goals': ['help b'], 'beliefs': ['secret']},
                       'b': {'location': 'hall', 'traits': 'cautious', 'goals': [], 'beliefs': []},
                       'c': {'location': 'yard', 'traits': 'curious', 'goals': [], 'beliefs': []}},
            'items': {'coin': 'a'}, 'facts': {'secret': 'The bridge is unsafe.'}}


class CoreTests(unittest.TestCase):
    def test_transfer_is_conserved_and_failed_attempt_atomic(self):
        w = World(scenario())
        w.act({'actor': 'a', 'kind': 'transfer', 'target': 'b', 'item': 'coin'})
        before = w.snapshot()
        with self.assertRaises(InvalidAction):
            w.act({'actor': 'a', 'kind': 'transfer', 'target': 'c', 'item': 'coin'})
        self.assertEqual(w.snapshot(), before)
        self.assertEqual(w.state['items']['coin'], 'b')

    def test_views_are_private_and_detached(self):
        w = World(scenario())
        view = w.view('b')
        self.assertEqual(view['beliefs'], {})
        self.assertNotIn('traits', view['nearby']['a'])
        self.assertNotIn('c', view['nearby'])
        view['self']['location'] = 'yard'
        self.assertEqual(w.state['actors']['b']['location'], 'hall')

    def test_information_has_a_transmission_path(self):
        w = World(scenario())
        with self.assertRaises(InvalidAction):
            w.act({'actor': 'b', 'kind': 'tell', 'target': 'a', 'fact': 'secret'})
        event = w.act({'actor': 'a', 'kind': 'tell', 'target': 'b', 'fact': 'secret'})
        self.assertIn('secret', w.view('b')['beliefs'])
        self.assertEqual(w.view('c')['events'], [])
        later = w.act({'actor': 'b', 'kind': 'wait', 'causes': [event['id']]})
        self.assertEqual(later['causes'], [event['id']])

    def test_cannot_cite_unseen_or_future_events(self):
        w = World(scenario())
        w.act({'actor': 'a', 'kind': 'wait'})
        for cause in [1, 999]:
            with self.assertRaises(InvalidAction):
                w.act({'actor': 'c', 'kind': 'wait', 'causes': [cause]})

    def test_promise_persists_and_expires(self):
        w = World(scenario())
        w.act({'actor': 'a', 'kind': 'promise', 'target': 'b', 'item': 'coin', 'due_in': 2})
        w.act({'actor': 'c', 'kind': 'wait'})
        w.act({'actor': 'c', 'kind': 'wait'})
        self.assertEqual(w.state['promises'][0]['status'], 'broken')
        restored = World.restore(w.snapshot())
        self.assertEqual(restored.snapshot(), w.snapshot())

    def test_promise_fulfilled_by_transfer(self):
        w = World(scenario())
        w.act({'actor': 'a', 'kind': 'promise', 'target': 'b', 'item': 'coin', 'due_in': 3})
        w.act({'actor': 'a', 'kind': 'transfer', 'target': 'b', 'item': 'coin'})
        self.assertEqual(w.state['promises'][0]['status'], 'fulfilled')

    def test_event_return_cannot_rewrite_history(self):
        w = World(scenario())
        event = w.act({'actor': 'a', 'kind': 'wait'})
        event['action']['kind'] = 'move'
        self.assertEqual(w.events[0]['action']['kind'], 'wait')

    def test_invalid_scenario(self):
        data = scenario()
        data['items']['coin'] = 'nobody'
        with self.assertRaises(ValueError):
            World(data)


if __name__ == '__main__':
    unittest.main()
