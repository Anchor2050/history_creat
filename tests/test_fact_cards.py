import unittest
from narrative.core import World
from narrative.story import history_packet, select_history
from test_world_v2 import rich


class FactCardTests(unittest.TestCase):
    def test_false_claim_is_rendered_as_false_claim(self):
        world=World(rich())
        world.act({'actor':'b','kind':'tell','target':'a','fact':'secret'})
        packet=history_packet(world,select_history(world))
        claim=packet['events'][0]['transmitted_claim']
        self.assertEqual(claim['statement'],'Bridge safe')
        self.assertFalse(claim['believed_value'])
        self.assertTrue(packet['world_facts']['secret']['actual_value'])
