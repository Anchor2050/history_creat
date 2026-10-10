import unittest
from narrative.longform.deep_replay import replay_packet, validate_replay_reply
from narrative.longform.era_context import context_as_of

class DeepReplayTests(unittest.TestCase):
 def test_future_fact_cannot_leak_into_early_2026(self):
  ids={x["id"] for x in context_as_of("2026-03-02")["observed"]}
  self.assertIn("china_ai_plus",ids)
  self.assertNotIn("frontier_math_2026",ids)
 def test_future_waves_are_scenarios(self):
  c=context_as_of("2026-10-11")
  self.assertTrue(c["future_scenarios"])
  self.assertTrue(all(x["status"]=="scenario" for x in c["future_scenarios"]))
 def test_packet_uses_frozen_as_of_context(self):
  run={"seed":1,"history":[{"week":1,"date":"2026-03-02","actors":{},"resources":{}}],"topology":{"nodes":[]}}
  p=replay_packet(run,1)
  self.assertEqual(p["as_of"],"2026-03-02")
  self.assertEqual(p["stage"],"deep_replay")
 def test_reply_cannot_invent_era_factor(self):
  run={"seed":1,"history":[{"week":1,"date":"2026-03-02","actors":{},"resources":{}}],"topology":{"nodes":[]}}
  p=replay_packet(run,1)
  reply={"actor":"lin_jing","choice":"wait","reason":"uncertain","actions":[],"era_factors_used":["invented_2030_fact"],"uncertainties":[],"counterfactual_rejected":"none"}
  with self.assertRaises(ValueError): validate_replay_reply(p,reply)

if __name__=="__main__": unittest.main()
