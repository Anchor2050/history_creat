import unittest
from narrative.longform.history_selector import assess_history, extract_history_line, pareto_histories

class HistorySelectorTests(unittest.TestCase):
    def sample(self, wid="w1"):
        return {"world_id":wid,"title":"x","premise":"p","events":[
            {"date":"2026-03-01","kind":"initial_condition","actors":["a"],"change":"start","causes":[],"motifs":["boundary"]},
            {"date":"2026-06-01","kind":"choice","actors":["a","b"],"change":"costly help","causes":["n1"],"costly_good":True,"respects_agency":True,"motifs":["boundary"]},
            {"date":"2027-01-01","kind":"echo","actors":["b","a"],"change":"returns","causes":["n2"],"delay_weeks":30,"earned_reversal":True,"motifs":["boundary"]},
        ],"unresolved":["career"]}
    def test_assessment_keeps_axes_separate(self):
        a=assess_history(self.sample())
        self.assertEqual(set(("truth","goodness","beauty"))-set(a),set())
        self.assertFalse(a["hard_truth_failure"])
    def test_authority_violation_cannot_be_compensated_by_beauty(self):
        h=self.sample(); h["events"][1]["authority_violation"]=True
        self.assertTrue(assess_history(h)["hard_truth_failure"])
        self.assertEqual(pareto_histories([h]),[])
    def test_extract_is_causal_beats_not_chapter_prose(self):
        line=extract_history_line(self.sample())
        self.assertEqual(line["world_id"],"w1")
        self.assertEqual(len(line["beats"]),3)
        self.assertIn("unresolved",line)

if __name__=="__main__": unittest.main()
