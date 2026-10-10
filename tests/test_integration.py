import tempfile
import unittest
from pathlib import Path
from narrative.run import run, load_world
from narrative.providers import ProviderError


class IntegrationTests(unittest.TestCase):
    def test_live_success_round_robin_and_story(self):
        class Client:
            calls = 0
            total_tokens = 0
            model = 'test'
            actors = []
            def json(self, instruction, state):
                self.calls += 1
                if 'Judge whether' in instruction:
                    return {'acceptable': True, 'reason': 'consistent'}
                if 'Plan a narrative' in instruction:
                    return {'scenes': [{'event_ids': [1, 2, 3], 'viewpoint': 'narrator', 'intent': 'waiting'}]}
                if 'Audit EACH' in instruction:
                    return {'checks': [{'unit': u['unit'], 'verdict': 'supported', 'evidence': ['initial'], 'reason': 'fixture'} for u in state['units']]}
                if 'Audit factual' in instruction:
                    return {'supported': True, 'issues': []}
                if 'Write a short' in instruction:
                    return {'scenes': [{'text': '三个人各自等待。', 'event_ids': [1, 2, 3], 'viewpoint': 'narrator'}]}
                self.actors.append(state['self']['id'])
                return {'action': {'actor': state['self']['id'], 'kind': 'wait'}}
        client = Client()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            w = run(output=output, steps=3, live=True, client=client, write_story=True)
            self.assertEqual(client.actors, ['he', 'lin', 'xu'])
            self.assertEqual(w.state['tick'], 3)
            self.assertTrue((output / 'story-draft.md').exists())

    def test_provider_failure_keeps_committed_history(self):
        class Client:
            calls = 0
            total_tokens = 0
            model = 'test'
            def json(self, instruction, state):
                self.calls += 1
                if self.calls == 3:
                    raise ProviderError('offline')
                if 'Judge whether' in instruction:
                    return {'acceptable': True, 'reason': 'consistent'}
                return {'action': {'actor': state['self']['id'], 'kind': 'wait'}}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            with self.assertRaises(ProviderError):
                run(output=output, steps=3, live=True, client=Client())
            self.assertEqual(load_world(output / 'checkpoint.json', resume=True).state['tick'], 1)
            self.assertIn('provider_error', (output / 'attempts.jsonl').read_text(encoding='utf-8'))

    def test_prevent_accidental_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            run(output=Path(folder), steps=1)
            with self.assertRaises(ValueError):
                run(output=Path(folder), steps=1)
