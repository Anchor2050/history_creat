import unittest
from pathlib import Path
from narrative.run import load_world


class ScenarioTests(unittest.TestCase):
    def test_three_different_rule_sets(self):
        expected = {'society': 'canal_open', 'civilization': 'warning_sent', 'mystery': 'door_open'}
        for name, flag in expected.items():
            with self.subTest(name=name):
                world = load_world(Path('narrative/scenarios') / (name + '.json'))
                for action in world.state['script']:
                    world.act(action)
                self.assertTrue(world.state['flags'][flag])
                self.assertEqual(len(world.events), 6)
                if name == 'society':
                    self.assertEqual(world.state['actors']['min']['goals'][0]['status'], 'failed')
                    self.assertEqual(world.state['organizations']['council']['resources']['food'], 1)
