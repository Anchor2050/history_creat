import unittest
from narrative.longform.ledger import Ledger, LedgerError


class LongformLedgerTests(unittest.TestCase):
    def ledger(self):
        return Ledger('2026-03-02', {'chen': 100, 'company': 1000, 'school': 5000}, {'chen': 4, 'supervisor': 2})

    def test_transfer_conserves_money_and_replay_does_not_pay_twice(self):
        ledger = self.ledger()
        result = ledger.transfer('pay-1', 'company', 'chen', 300, 'accepted delivery')
        self.assertEqual(sum(ledger.snapshot()['accounts'].values()), 6100)
        before = ledger.snapshot()
        self.assertEqual(ledger.transfer('pay-1', 'company', 'chen', 300, 'accepted delivery'), result)
        self.assertEqual(ledger.snapshot(), before)
        with self.assertRaises(LedgerError):
            ledger.transfer('pay-1', 'company', 'chen', 200, 'accepted delivery')
        self.assertEqual(ledger.snapshot(), before)

    def test_insufficient_funds_is_atomic(self):
        ledger = self.ledger(); before = ledger.snapshot()
        with self.assertRaises(LedgerError):
            ledger.transfer('bad', 'chen', 'company', 101, 'cannot afford')
        self.assertEqual(ledger.snapshot(), before)

    def test_calendar_booking_blocks_overlap_and_is_atomic(self):
        ledger = self.ledger()
        ledger.reserve('work', [{'actor': 'chen', 'start': '2026-03-02T09:00', 'end': '2026-03-02T11:00'}], 'analysis')
        before = ledger.snapshot()
        with self.assertRaises(LedgerError):
            ledger.reserve('meeting', [
                {'actor': 'supervisor', 'start': '2026-03-02T10:00', 'end': '2026-03-02T11:00'},
                {'actor': 'chen', 'start': '2026-03-02T10:00', 'end': '2026-03-02T11:00'}], 'meeting')
        self.assertEqual(ledger.snapshot(), before)

    def test_cross_week_task_reserves_future_capacity(self):
        ledger = self.ledger()
        ledger.reserve('task', [
            {'actor': 'chen', 'start': '2026-03-06T09:00', 'end': '2026-03-06T12:00'},
            {'actor': 'chen', 'start': '2026-03-09T09:00', 'end': '2026-03-09T12:00'}], 'multiweek work')
        self.assertEqual(ledger.used_minutes('chen', '2026-03-03'), 180)
        self.assertEqual(ledger.used_minutes('chen', '2026-03-10'), 180)
        before = ledger.snapshot()
        with self.assertRaises(LedgerError):
            ledger.reserve('extra', [{'actor': 'chen', 'start': '2026-03-10T09:00', 'end': '2026-03-10T11:00'}], 'overcommit')
        self.assertEqual(ledger.snapshot(), before)

    def test_completed_work_does_not_restore_weekly_capacity(self):
        ledger = self.ledger()
        ledger.reserve('work', [{'actor': 'chen', 'start': '2026-03-02T09:00', 'end': '2026-03-02T13:00'}], 'analysis')
        ledger.advance('2026-03-03')
        self.assertEqual(ledger.used_minutes('chen', '2026-03-03'), 240)
        with self.assertRaises(LedgerError):
            ledger.reserve('more', [{'actor': 'chen', 'start': '2026-03-03T09:00', 'end': '2026-03-03T10:00'}], 'more')
        self.assertEqual(ledger.snapshot()['reservations'][0]['status'], 'completed')

    def test_due_payment_waits_for_actual_funds_and_recovers(self):
        ledger = self.ledger()
        ledger.schedule_payment('bill', 'chen', 'company', 300, '2026-03-03', 'bill')
        ledger.schedule_payment('stipend', 'school', 'chen', 400, '2026-03-05', 'stipend')
        ledger.advance('2026-03-04')
        self.assertEqual(ledger.snapshot()['payments']['bill']['status'], 'blocked')
        self.assertEqual(ledger.snapshot()['accounts']['chen'], 100)
        ledger.advance('2026-03-06')
        state = ledger.snapshot()
        self.assertEqual(state['accounts']['chen'], 200)
        self.assertEqual(state['payments']['bill']['paid_at'], '2026-03-05T00:00:00')
        restored = Ledger.restore(state)
        restored.advance('2026-03-06')
        self.assertEqual(restored.snapshot(), state)

    def test_cancellation_releases_only_unstarted_booking(self):
        ledger = self.ledger()
        ledger.reserve('work', [{'actor': 'chen', 'start': '2026-03-04T09:00', 'end': '2026-03-04T11:00'}], 'analysis')
        ledger.cancel('cancel-1', 'work:1', 'new priority')
        self.assertEqual(ledger.used_minutes('chen', '2026-03-04'), 0)
        ledger.reserve('new', [{'actor': 'chen', 'start': '2026-03-04T09:00', 'end': '2026-03-04T11:00'}], 'other')
        ledger.advance('2026-03-04T10:00')
        with self.assertRaises(LedgerError):
            ledger.cancel('cancel-2', 'new:1', 'cannot erase spent time')

    def test_restore_rejects_forged_balances_and_time_cannot_reverse(self):
        ledger = self.ledger(); state = ledger.snapshot()
        state['accounts']['chen'] += 1
        with self.assertRaises(LedgerError):
            Ledger.restore(state)
        with self.assertRaises(LedgerError):
            ledger.advance('2026-03-01')
