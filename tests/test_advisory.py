import tempfile
import unittest
from pathlib import Path
from narrative.run import run


class AdvisoryTests(unittest.TestCase):
    def test_soft_judgment_does_not_override_legal_character_choice(self):
        class Client:
            calls=0
            total_tokens=0
            model='test'
            def json(self,prompt,state):
                self.calls+=1
                if 'Judge whether' in prompt:
                    return {'acceptable':False,'reason':'not efficient enough'}
                return {'action':{'actor':state['self']['id'],'kind':'wait'},'reason':'chooses caution'}
        with tempfile.TemporaryDirectory() as folder:
            world=run(output=Path(folder),steps=1,live=True,client=Client())
            self.assertEqual(len(world.events),1)
            self.assertEqual(world.events[0]['intention'],'chooses caution')
