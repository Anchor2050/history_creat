import unittest
from narrative.providers import DeepSeek, ProviderError


class ProviderV2Tests(unittest.TestCase):
    def test_truncation_is_accounted_and_diagnosed(self):
        def transport(*args):
            return {'choices': [{'finish_reason': 'length', 'message': {'content': ''}}], 'usage': {'total_tokens': 2020}}
        client = DeepSeek('test', transport=transport)
        with self.assertRaisesRegex(ProviderError, 'length'):
            client.json('json', {})
        self.assertEqual(client.total_tokens, 2020)
        self.assertEqual(client.diagnostics[-1]['finish_reason'], 'length')

    def test_non_thinking_request(self):
        requests = []
        def transport(url, headers, body, timeout):
            requests.append(body)
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}
        client = DeepSeek('test', transport=transport, thinking=False)
        client.json('json', {})
        self.assertEqual(requests[0]['thinking'], {'type': 'disabled'})

    def test_default_reasoning_has_output_headroom(self):
        requests = []
        def transport(url, headers, body, timeout):
            requests.append(body)
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}
        DeepSeek('test', transport=transport).json('json', {})
        self.assertEqual(requests[0]['thinking'], {'type': 'enabled'})
        self.assertEqual(requests[0]['max_tokens'], 8192)
