import unittest

from narrative.longform.macro_bridge import (
    MacroBridgeError,
    actor_macro_view,
    freeze_macro_views,
)
from narrative.longform.macro_world import MacroWorld, beijing_2026_macro


class MacroBridgeTests(unittest.TestCase):
    def make_world(self):
        return MacroWorld(beijing_2026_macro())

    def test_same_macro_world_reaches_characters_differently(self):
        world = self.make_world()
        world.advance("2030-01-01")
        chen = actor_macro_view(world, "chen_lan")
        zhao = actor_macro_view(world, "zhao_ke")
        self.assertNotEqual(chen["pressure"]["net_pressure"], zhao["pressure"]["net_pressure"])
        self.assertNotEqual(
            {x["signal"] for x in chen["pressure"]["components"]},
            {x["signal"] for x in zhao["pressure"]["components"]},
        )

    def test_public_shock_only_reaches_exposed_actor(self):
        world = self.make_world()
        world.advance("2028-09-01")
        xu = actor_macro_view(world, "xu_hang")
        self.assertTrue(any(x["change_id"] == "ai-tool-jump-2028" for x in xu["recent_public_changes"]))

    def test_frozen_views_are_independent_copies(self):
        world = self.make_world()
        views = freeze_macro_views(world, ["lin_jing", "chen_lan"])
        views["lin_jing"]["notices"].append({"code": "fake"})
        fresh = actor_macro_view(world, "lin_jing")
        self.assertFalse(any(x.get("code") == "fake" for x in fresh["notices"]))

    def test_unknown_actor_rejected(self):
        with self.assertRaises(MacroBridgeError):
            actor_macro_view(self.make_world(), "nobody")


if __name__ == "__main__":
    unittest.main()
