import unittest
from narrative.story import audit_sentences
from narrative.providers import ProviderError

class SentenceAuditTests(unittest.TestCase):
    def client(self, rows):
        class Client:
            def json(self, instruction, state):
                return {'checks': rows}
        return Client()

    def test_missing_sentence_cannot_pass(self):
        draft = {'scenes': [{'text': 'He waited. She left.', 'event_ids': [1], 'viewpoint': 'narrator'}]}
        with self.assertRaises(ProviderError):
            audit_sentences({'events': [{'id': 1}]}, draft, self.client([]))

    def test_unknown_evidence_cannot_pass(self):
        draft = {'scenes': [{'text': 'He waited.', 'event_ids': [1], 'viewpoint': 'narrator'}]}
        with self.assertRaises(ProviderError):
            audit_sentences({'events': [{'id': 1}]}, draft, self.client([
                {'unit': 0, 'verdict': 'supported', 'evidence': ['E99'], 'reason': 'wait'}]))

    def test_uncertainty_requires_revision(self):
        draft = {'scenes': [{'text': 'He was angry.', 'event_ids': [1], 'viewpoint': 'narrator'}]}
        result = audit_sentences({'events': [{'id': 1}]}, draft, self.client([
            {'unit': 0, 'verdict': 'uncertain', 'evidence': ['initial'], 'reason': 'No recorded emotion'}]))
        self.assertFalse(result['supported'])
        self.assertEqual(result['units'][0]['text'], 'He was angry.')

    def test_malformed_verdict_is_recoverable_provider_error(self):
        draft = {'scenes': [{'text': 'He waited.', 'event_ids': [1], 'viewpoint': 'narrator'}]}
        with self.assertRaises(ProviderError):
            audit_sentences({'events': [{'id': 1}]}, draft, self.client([
                {'unit': 0, 'verdict': [], 'evidence': ['E1'], 'reason': 'malformed'}]))
