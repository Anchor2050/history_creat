import unittest
from narrative.providers import DeepSeek, Judge, ProviderError


class ProviderTests(unittest.TestCase):
    def test_deepseek_payload_and_call_budget(self):
        requests = []
        def transport(url, headers, body, timeout):
            requests.append((url, headers, body))
            return {'choices': [{'message': {'content': '{"ok":true}'}, 'finish_reason': 'stop'}], 'usage': {'total_tokens': 10}}
        client = DeepSeek('secret', transport=transport, max_calls=1)
        self.assertEqual(client.json('return JSON', {'x': 1}), {'ok': True})
        self.assertIn('api.deepseek.com', requests[0][0])
        self.assertEqual(requests[0][2]['response_format'], {'type': 'json_object'})
        with self.assertRaises(ProviderError):
            client.json('again', {})
        self.assertEqual(len(requests), 1)

    def test_optional_judge_failure_falls_back(self):
        class Broken:
            def evaluate(self, view, action):
                raise RuntimeError('secret must not leak')
        class Client:
            def json(self, prompt, payload):
                return {'acceptable': True, 'reason': 'consistent'}
        result = Judge(Client(), optional=Broken()).evaluate({}, {})
        self.assertEqual(result['provider'], 'deepseek')
        self.assertEqual(result['fallback'], 'RuntimeError')
        self.assertNotIn('secret', str(result))

    def test_invalid_judge_output_is_not_approval(self):
        class Client:
            def json(self, prompt, payload):
                return {'acceptable': 'false', 'reason': 'bad'}
        with self.assertRaises(ProviderError):
            Judge(Client()).evaluate({}, {})

    def test_truncated_and_non_json_responses_fail(self):
        for content, finish in [('{}', 'length'), ('not json', 'stop')]:
            client = DeepSeek('key', transport=lambda *args: {'choices': [{'message': {'content': content}, 'finish_reason': finish}]})
            with self.assertRaises(ProviderError):
                client.json('JSON', {})

    def test_transport_error_is_sanitized(self):
        def broken(*args):
            raise RuntimeError('credential=secret')
        with self.assertRaises(ProviderError) as cm:
            DeepSeek('secret', transport=broken).json('JSON', {})
        self.assertNotIn('secret', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
