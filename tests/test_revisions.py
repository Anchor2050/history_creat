import unittest
from narrative.core import World
from narrative.story import create_story
from narrative.providers import ProviderError
from test_world_v2 import rich

class RevisionClient:
    def __init__(self, fail_audit_once=False, always_bad=False):
        self.writes=0
        self.fail_audit_once=fail_audit_once
        self.always_bad=always_bad
    def json(self,prompt,state):
        if 'Plan a narrative' in prompt:
            return {'scenes':[{'event_ids':[1],'viewpoint':'narrator','intent':'wait'}]}
        if 'Write a short' in prompt or 'Revise the draft' in prompt:
            self.writes+=1
            return {'scenes':[{'event_ids':[1],'viewpoint':'narrator','text':'He waited.'}]}
        if 'Audit factual' in prompt:
            if self.fail_audit_once:
                self.fail_audit_once=False
                raise ProviderError('temporary')
            return {'supported':self.writes>1 and not self.always_bad,'issues':[] if self.writes>1 and not self.always_bad else ['unsupported detail']}
        if 'Audit EACH' in prompt:
            return {'checks':[{'unit':u['unit'],'verdict':'supported','evidence':['E1'],'reason':'recorded wait'} for u in state['units']]}
        raise AssertionError(prompt)

class RevisionTests(unittest.TestCase):
    def world(self):
        w=World(rich());w.act({'actor':'a','kind':'wait'});return w
    def test_automatic_revision_preserves_failed_draft(self):
        c=RevisionClient()
        result=create_story(self.world(),c,max_revisions=2)
        self.assertEqual(c.writes,2)
        self.assertEqual(result['status'],'model_review_passed')
        self.assertEqual(len(result['attempts']),2)
        self.assertFalse(result['attempts'][0]['review']['supported'])
    def test_revision_limit_is_not_success(self):
        result=create_story(self.world(),RevisionClient(always_bad=True),max_revisions=1)
        self.assertEqual(len(result['attempts']),2)
        self.assertEqual(result['status'],'needs_revision')
    def test_resume_reuses_saved_draft(self):
        saved=[]; c=RevisionClient(fail_audit_once=True);w=self.world()
        with self.assertRaises(ProviderError):
            create_story(w,c,max_revisions=0,progress=lambda p:saved.append(p))
        self.assertEqual(c.writes,1)
        create_story(w,c,max_revisions=0,checkpoint=saved[-1])
        self.assertEqual(c.writes,1)

    def test_invalid_audit_is_saved_and_sent_back_for_correction(self):
        class FormatClient(RevisionClient):
            bad = True
            received_feedback = False
            def json(self, prompt, state):
                if 'Audit EACH' in prompt:
                    if self.bad:
                        self.bad = False
                        return {'checks': []}
                    self.received_feedback = bool(state['previous_invalid_responses'])
                return super().json(prompt, state)
        saved = []; c = FormatClient(); w = self.world()
        with self.assertRaises(ProviderError):
            create_story(w, c, progress=lambda p: saved.append(p))
        self.assertEqual(saved[-1]['attempts'][0]['audit_failures'][0]['response'], {'checks': []})
        create_story(w, c, checkpoint=saved[-1])
        self.assertTrue(c.received_feedback)
        self.assertEqual(c.writes, 1)
