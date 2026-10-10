import unittest
from narrative.core import World
from narrative.story import history_packet, select_history
from test_world_v2 import rich


class HistorianTests(unittest.TestCase):
    def test_initial_location_survives_moves_and_restore(self):
        world=World(rich())
        world.act({'actor':'a','kind':'move','target':'yard'})
        packet=history_packet(World.restore(world.snapshot()),select_history(world))
        self.assertEqual(packet['initial']['actors']['a']['location'],'hall')
        self.assertNotIn('script',packet['initial'])

    def test_private_view_has_public_rules_without_secret_effects(self):
        s=rich()
        s['rules']['repair']['effects']['reveal']=['secret']
        view=World(s).view('c')
        self.assertIn('repair',view['public_rules'])
        self.assertNotIn('reveal',str(view['public_rules']))
        self.assertNotIn('Bridge unsafe',str(view))
