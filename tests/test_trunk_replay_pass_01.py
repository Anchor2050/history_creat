import unittest
from narrative.longform.trunk_replay_pass_01 import TRUNK_REPLAY_PASS_01, validate_continuity

class TrunkReplayPass01Tests(unittest.TestCase):
    def test_continuity(self):
        result=validate_continuity()
        self.assertTrue(result["valid"],result)
        self.assertEqual(result["nodes"],18)
    def test_no_future_causes(self):
        seen=set()
        for n in TRUNK_REPLAY_PASS_01:
            self.assertTrue(set(n.get("causes",[]))<=seen)
            seen.add(n["id"])
    def test_every_choice_has_rejected_counterfactual(self):
        self.assertTrue(all(n.get("rejected") for n in TRUNK_REPLAY_PASS_01))

if __name__=="__main__": unittest.main()
