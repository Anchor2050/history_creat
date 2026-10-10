import unittest
from narrative.longform.exchange import Exchange, ExchangeError


class ExchangeTests(unittest.TestCase):
    def test_zero_api_request_and_resume(self):
        exchange = Exchange('run-1')
        task = exchange.request('decision', 'state-a', {'actor': 'chen', 'known': [1]}, 'Decide', {'action': 'object'})
        restored = Exchange.restore(exchange.snapshot())
        self.assertEqual(restored.pending(), task)
        reply = {'task_id': task['task_id'], 'input_hash': task['input_hash'], 'state_hash': 'state-a', 'result': {'action': 'wait'}, 'driver': 'chat'}
        received = restored.receive(reply, 'state-a')
        self.assertEqual(received['status'], 'received')
        self.assertEqual(restored.snapshot()['history'], [])
        receipt = restored.commit(task['task_id'], 'state-a', {'accepted': True, 'event_id': 1}, 'state-b')
        self.assertEqual(receipt['status'], 'committed')
        self.assertEqual(restored.receive(reply, 'state-b'), receipt)
        self.assertIsNone(restored.pending())
        self.assertEqual(Exchange.restore(restored.snapshot()).snapshot(), restored.snapshot())

    def test_stale_reply_and_conflicting_retry_do_not_change_state(self):
        x = Exchange('r'); t = x.request('write', 'a', {}, 'Write', {})
        reply = dict(task_id=t['task_id'], input_hash=t['input_hash'], state_hash='a', result={'text': 'first'}, driver='chat')
        before = x.snapshot()
        with self.assertRaises(ExchangeError): x.receive(reply, 'b')
        self.assertEqual(x.snapshot(), before)
        x.receive(reply, 'a'); before = x.snapshot()
        with self.assertRaises(ExchangeError): x.receive({**reply, 'result': {'text': 'different'}}, 'a')
        self.assertEqual(x.snapshot(), before)

    def test_pending_request_cannot_be_overwritten_or_committed_without_response(self):
        x = Exchange('r'); t = x.request('decide', 'a', {}, 'Act', {})
        self.assertEqual(x.request('decide', 'a', {}, 'Act', {}), t)
        with self.assertRaises(ExchangeError): x.request('decide', 'b', {}, 'Act', {})
        with self.assertRaises(ExchangeError): x.commit(t['task_id'], 'a', {}, 'b')

    def test_snapshot_hash_detects_modified_task(self):
        x = Exchange('r'); x.request('decide', 'a', {'known': [1]}, 'Act', {})
        state = x.snapshot(); state['pending']['task']['context']['known'].append(99)
        with self.assertRaises(ExchangeError): Exchange.restore(state)

    def test_same_input_new_task_after_commit_is_distinct(self):
        x = Exchange('r'); t = x.request('decide', 'a', {}, 'Act', {})
        x.receive(dict(task_id=t['task_id'], input_hash=t['input_hash'], state_hash='a', result={}, driver='deepseek'), 'a')
        x.commit(t['task_id'], 'a', {'accepted': False, 'reason': 'illegal'}, 'a')
        t2 = x.request('decide', 'a', {}, 'Act', {})
        self.assertNotEqual(t['task_id'], t2['task_id'])
