import random
import unittest
from pathlib import Path
from narrative.run import load_world
from narrative.core import World


class SimulationInvariantTests(unittest.TestCase):
    def test_mixed_actions_preserve_invariants_and_snapshots(self):
        for scenario in ['society','civilization','mystery']:
            w=load_world(Path('narrative/scenarios')/(scenario+'.json'))
            rng=random.Random(42)
            names=list(w.state['actors'])
            for step in range(30):
                name=names[step%len(names)]
                choices=w.actions(name)
                action=rng.choice(choices)
                event=w.act(action)
                self.assertTrue(all(parent<event['id'] for parent in event['dependencies']))
                for actor in w.state['actors'].values():
                    self.assertTrue(all(n>=0 for n in actor['resources'].values()))
                for org in w.state['organizations'].values():
                    self.assertTrue(all(n>=0 for n in org['resources'].values()))
                self.assertEqual(w.snapshot(),World.restore(w.snapshot()).snapshot())
