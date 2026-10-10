import tempfile
import unittest
from pathlib import Path
from narrative.run import run, load_world


class ResumeTests(unittest.TestCase):
    def test_rejected_attempt_advances_persisted_turn(self):
        class Client:
            calls = 0
            total_tokens = 0
            model = 'test'
            names = []
            def json(self, prompt, state):
                self.calls += 1
                if 'Judge whether' in prompt:
                    return {'acceptable': True, 'reason': 'ok'}
                self.names.append(state['self']['id'])
                return {'action': {'actor': 'invalid', 'kind': 'wait'}}
        c = Client()
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            run(output=out, live=True, steps=1, client=c)
            run(output=out, live=True, steps=1, client=c, resume=out/'checkpoint.json')
            self.assertEqual(c.names, ['he', 'lin'])
            self.assertEqual(load_world(out/'checkpoint.json', resume=True).runtime['attempts'], 2)
