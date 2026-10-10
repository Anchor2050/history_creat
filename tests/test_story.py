import unittest
from narrative.core import World
from narrative.story import select_history, validate_scenes, create_story
from narrative.providers import ProviderError
from test_world_v2 import rich


class StoryTests(unittest.TestCase):
    def test_selection_keeps_dependencies(self):
        w = World(rich())
        w.act({'actor': 'a', 'kind': 'promise', 'target': 'b', 'item': 'coin', 'due_in': 4})
        w.act({'actor': 'c', 'kind': 'wait'})
        w.act({'actor': 'a', 'kind': 'transfer', 'target': 'b', 'item': 'coin'})
        selected = select_history(w, limit=1)
        ids = {e['id'] for e in selected}
        self.assertIn(3, ids)
        self.assertIn(1, ids)

    def test_unknown_citation_and_viewpoint_rejected(self):
        w = World(rich())
        w.act({'actor': 'a', 'kind': 'wait'})
        for scene in [{'event_ids': [999], 'viewpoint': 'a'}, {'event_ids': [1], 'viewpoint': 'ghost'}]:
            with self.assertRaises(ProviderError):
                validate_scenes([scene], w, {1})

    def test_failed_fact_review_is_explicit(self):
        w = World(rich())
        w.act({'actor': 'a', 'kind': 'wait'})
        class Client:
            def json(self, prompt, state):
                if 'Plan a narrative' in prompt:
                    return {'scenes': [{'event_ids': [1], 'viewpoint': 'a', 'intent': 'waiting'}]}
                if 'Audit EACH' in prompt:
                    return {'checks': [{'unit': u['unit'], 'verdict': 'supported', 'evidence': ['initial'], 'reason': 'fixture'} for u in state['units']]}
                if 'Audit factual' in prompt:
                    return {'supported': False, 'issues': ['invented event']}
                return {'scenes': [{'event_ids': [1], 'viewpoint': 'a', 'text': 'Invented event'}]}
        result = create_story(w, Client())
        self.assertEqual(result['status'], 'needs_revision')
        self.assertFalse(result['review']['supported'])
