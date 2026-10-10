import tempfile
import unittest
from pathlib import Path
from narrative.autorun import run_job
from narrative.run import DEMO
from narrative.providers import ProviderError

class JobClient:
    model='test'; thinking=True; max_output_tokens=8192
    def __init__(self,max_calls=100):
        self.calls=0;self.total_tokens=0;self.max_calls=max_calls;self.diagnostics=[]
    def json(self,prompt,state):
        if self.calls>=self.max_calls: raise ProviderError('budget')
        self.calls+=1
        if 'Judge whether' in prompt:return {'acceptable':True,'reason':'okay'}
        if 'Reflect as' in prompt:return {'text':'I will reconsider waiting.', 'evidence':[state['events'][-1]['id']]}
        if 'Plan a narrative' in prompt:return {'scenes':[{'event_ids':[state['events'][-1]['id']],'viewpoint':'narrator','intent':'wait'}]}
        if 'Write a short' in prompt or 'Revise the draft' in prompt:return {'scenes':[{'event_ids':state['outline']['scenes'][0]['event_ids'],'viewpoint':'narrator','text':'They waited.'}]}
        if 'Audit factual' in prompt:return {'supported':True,'issues':[]}
        if 'Audit EACH' in prompt:return {'checks':[{'unit':u['unit'],'verdict':'supported','evidence':['initial'],'reason':'fixture'} for u in state['units']]}
        return {'choice':0,'reason':'wait','causes':[]}

class AutonomousTests(unittest.TestCase):
    def test_two_rounds_without_operator(self):
        with tempfile.TemporaryDirectory() as folder:
            job=run_job(output=folder,scenario=DEMO,rounds=2,steps_per_round=1,client=JobClient())
            self.assertEqual(job['status'],'completed')
            self.assertEqual(len(job['results']),2)
            self.assertTrue((Path(folder)/'round-0002'/'story-draft.md').exists())
    def test_budget_resume_does_not_repeat_committed_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            job=run_job(output=folder,scenario=DEMO,rounds=1,steps_per_round=2,client=JobClient(2))
            self.assertEqual(job['status'],'budget_exhausted')
            job=run_job(output=folder,resume=True,client=JobClient())
            self.assertEqual(job['status'],'completed')
            self.assertEqual(job['results'][0]['events_total'],2)

    def test_failed_review_retries_only_unfinished_stage(self):
        class TransientClient(JobClient):
            writes = 0
            failed = False
            def json(self, prompt, state):
                if 'Write a short' in prompt:
                    self.writes += 1
                if 'Audit factual' in prompt and not self.failed:
                    self.failed = True
                    self.calls += 1
                    raise ProviderError('temporary transport error')
                return super().json(prompt, state)
        with tempfile.TemporaryDirectory() as folder:
            client = TransientClient()
            job = run_job(output=folder, scenario=DEMO, rounds=1, steps_per_round=1, client=client)
            self.assertEqual(job['status'], 'completed')
            self.assertEqual(len(job['errors']), 1)
            self.assertEqual(client.writes, 1)
            before = client.calls
            run_job(output=folder, resume=True, client=client)
            self.assertEqual(client.calls, before)

    def test_exhausted_retries_are_saved_as_failure(self):
        class FailingClient(JobClient):
            def json(self, prompt, state):
                self.calls += 1
                raise ProviderError('unavailable')
        with tempfile.TemporaryDirectory() as folder:
            client = FailingClient()
            job = run_job(output=folder, scenario=DEMO, rounds=1, steps_per_round=1, client=client, retries=2)
            self.assertEqual(job['status'], 'failed')
            self.assertEqual(client.calls, 3)
            self.assertTrue((Path(folder) / 'job-report.json').exists())

    def test_truncation_increases_headroom_within_ceiling(self):
        class TruncatedClient(JobClient):
            def json(self, prompt, state):
                if self.max_output_tokens < 16384:
                    self.calls += 1
                    raise ProviderError('Incomplete generation: length')
                return super().json(prompt, state)
        with tempfile.TemporaryDirectory() as folder:
            client = TruncatedClient()
            job = run_job(output=folder, scenario=DEMO, rounds=1, steps_per_round=1,
                          client=client, max_output_ceiling=16384)
            self.assertEqual(job['status'], 'completed')
            self.assertEqual(client.max_output_tokens, 16384)
            self.assertEqual(job['output_token_limit'], 16384)

    def test_report_preserves_rejections_and_stagnation(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            run_job(output=folder, scenario=DEMO, rounds=1, steps_per_round=2, client=JobClient())
            report = json.loads((Path(folder) / 'job-report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['activity']['wait_actions'], 2)
            self.assertEqual(report['activity']['no_change_beyond_time'], 2)
        class InvalidClient(JobClient):
            def json(self, prompt, state):
                self.calls += 1
                return {'action': {'actor': 'nonexistent', 'kind': 'wait'}}
        with tempfile.TemporaryDirectory() as folder:
            run_job(output=folder, scenario=DEMO, rounds=1, steps_per_round=2, client=InvalidClient())
            report = json.loads((Path(folder) / 'job-report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['activity']['attempt_statuses']['rejected'], 2)
            self.assertEqual(report['activity']['committed_events'], 0)
