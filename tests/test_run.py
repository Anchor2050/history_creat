import json
import tempfile
import unittest
from pathlib import Path
from narrative.run import run, load_world


class RunnerTests(unittest.TestCase):
    def test_offline_run_and_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            run(output=output, steps=5, live=False)
            checkpoint = output / 'checkpoint.json'
            world = load_world(checkpoint, resume=True)
            self.assertEqual(world.state['tick'], 5)
            self.assertEqual(world.state['items']['medicine'], 'lin')
            self.assertIn('bridge', world.view('lin')['beliefs'])
            self.assertEqual(world.state['promises'][0]['status'], 'fulfilled')
            run(output=output, steps=1, live=False, resume=checkpoint)
            self.assertEqual(load_world(checkpoint, resume=True).state['tick'], 6)
            self.assertTrue((output / 'history.md').exists())

    def test_live_with_injected_client_and_rejected_action(self):
        class Client:
            calls = 0
            total_tokens = 0
            model = 'test'
            def json(self, instruction, state):
                self.calls += 1
                if 'Judge whether' in instruction:
                    return {'acceptable': True, 'reason': 'plausible'}
                return {'action': {'actor': 'fake', 'kind': 'wait'}}
        with tempfile.TemporaryDirectory() as folder:
            run(output=Path(folder), steps=2, live=True, client=Client())
            checkpoint = json.loads((Path(folder) / 'checkpoint.json').read_text(encoding='utf-8'))
            self.assertEqual(checkpoint['state']['tick'], 0)
            attempts = (Path(folder) / 'attempts.jsonl').read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(attempts), 2)
            self.assertTrue(all(json.loads(a)['status'] == 'rejected' for a in attempts))


if __name__ == '__main__':
    unittest.main()
