"""Transactional money and calendar capacity. No model can manufacture either."""
from copy import deepcopy
from datetime import datetime, timedelta


class LedgerError(ValueError):
    pass


def moment(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise LedgerError('Use an ISO local story date/time') from None
    if parsed.tzinfo is not None or parsed.second or parsed.microsecond:
        raise LedgerError('Story time must be local and aligned to whole minutes')
    return parsed


def week_start(value):
    when = moment(value)
    return (when - timedelta(days=when.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def week_parts(start, end):
    cursor, finish = moment(start), moment(end)
    while cursor < finish:
        monday = week_start(cursor.isoformat())
        stop = min(finish, monday + timedelta(days=7))
        yield monday.date().isoformat(), int((stop - cursor).total_seconds() // 60)
        cursor = stop


class Ledger:
    def __init__(self, now, accounts, weekly_hours):
        self.state = {'version': 1, 'now': moment(now).isoformat(),
                      'accounts': deepcopy(accounts), 'initial_accounts': deepcopy(accounts),
                      'weekly_hours': deepcopy(weekly_hours), 'reservations': [], 'payments': {},
                      'operations': {}, 'journal': []}
        self._validate(self.state)

    def snapshot(self):
        return deepcopy(self.state)

    @classmethod
    def restore(cls, snapshot):
        state = deepcopy(snapshot)
        cls._validate(state)
        ledger = cls.__new__(cls)
        ledger.state = state
        return ledger

    @staticmethod
    def _log(state, kind, **fields):
        entry = {'id': len(state['journal']) + 1, 'at': state['now'], 'kind': kind, **fields}
        state['journal'].append(entry)
        return deepcopy(entry)

    @staticmethod
    def _validate(state):
        if state.get('version') != 1:
            raise LedgerError('Unsupported ledger snapshot')
        moment(state['now'])
        for field in ('accounts', 'initial_accounts', 'weekly_hours'):
            values = state[field]
            if not isinstance(values, dict) or any(not isinstance(k, str) or not k or type(v) is not int or v < 0 for k, v in values.items()):
                raise LedgerError('Account balances and weekly hours must be nonnegative integers')
        replay = dict(state['initial_accounts'])
        if set(replay) != set(state['accounts']):
            raise LedgerError('Account identities changed')
        for index, entry in enumerate(state['journal'], 1):
            if entry['id'] != index or moment(entry['at']) > moment(state['now']):
                raise LedgerError('Invalid journal sequence/time')
            if entry['kind'] == 'transfer':
                Ledger._money_args(state, entry['source'], entry['target'], entry['amount'])
                replay[entry['source']] -= entry['amount']
                replay[entry['target']] += entry['amount']
                if replay[entry['source']] < 0:
                    raise LedgerError('Journal spends unavailable funds')
        if replay != state['accounts']:
            raise LedgerError('Balances disagree with double-entry history')
        seen, active, weekly = set(), [], {}
        for reservation in state['reservations']:
            if reservation['id'] in seen or reservation['actor'] not in state['weekly_hours']:
                raise LedgerError('Invalid reservation identity')
            seen.add(reservation['id'])
            start, end = moment(reservation['start']), moment(reservation['end'])
            if end <= start or reservation['status'] not in {'booked', 'completed', 'cancelled'}:
                raise LedgerError('Invalid reservation interval/status')
            if reservation['status'] == 'cancelled':
                continue
            for other in active:
                if other['actor'] == reservation['actor'] and start < moment(other['end']) and moment(other['start']) < end:
                    raise LedgerError('Calendar overlap')
            active.append(reservation)
            for week, minutes in week_parts(reservation['start'], reservation['end']):
                key = (reservation['actor'], week)
                weekly[key] = weekly.get(key, 0) + minutes
                if weekly[key] > state['weekly_hours'][reservation['actor']] * 60:
                    raise LedgerError('Weekly time capacity exceeded')
        for key, payment in state['payments'].items():
            if payment['id'] != key or payment['status'] not in {'scheduled', 'blocked', 'paid'}:
                raise LedgerError('Invalid scheduled payment')
            Ledger._money_args(state, payment['source'], payment['target'], payment['amount'])
            moment(payment['due'])

    @staticmethod
    def _money_args(state, source, target, amount):
        if source not in state['accounts'] or target not in state['accounts'] or source == target or type(amount) is not int or amount <= 0:
            raise LedgerError('Transfer needs distinct known accounts and a positive integer amount')

    def _operation(self, identifier, payload, apply):
        if not isinstance(identifier, str) or not identifier or not isinstance(payload.get('reason'), str) or not payload['reason'].strip():
            raise LedgerError('Operation needs an ID and reason')
        prior = self.state['operations'].get(identifier)
        if prior:
            if prior['payload'] != payload:
                raise LedgerError('Operation ID reused with different contents')
            return deepcopy(prior['result'])
        state = self.snapshot()
        result = apply(state)
        state['operations'][identifier] = {'payload': deepcopy(payload), 'result': deepcopy(result)}
        self._validate(state)
        self.state = state
        return deepcopy(result)

    @classmethod
    def _transfer(cls, state, source, target, amount, reason, operation):
        cls._money_args(state, source, target, amount)
        if state['accounts'][source] < amount:
            raise LedgerError('Insufficient funds')
        state['accounts'][source] -= amount
        state['accounts'][target] += amount
        return cls._log(state, 'transfer', source=source, target=target, amount=amount, reason=reason, operation=operation)

    def transfer(self, identifier, source, target, amount, reason):
        payload = dict(kind='transfer', source=source, target=target, amount=amount, reason=reason)
        return self._operation(identifier, payload, lambda state: self._transfer(state, source, target, amount, reason, identifier))

    def reserve(self, identifier, slots, reason):
        if not isinstance(slots, list) or not slots:
            raise LedgerError('A reservation needs at least one calendar slot')
        normalized = []
        for slot in slots:
            if not isinstance(slot, dict) or set(slot) != {'actor', 'start', 'end'}:
                raise LedgerError('A slot needs actor, start and end')
            normalized.append({'actor': slot['actor'], 'start': moment(slot['start']).isoformat(), 'end': moment(slot['end']).isoformat()})
        def apply(state):
            rows = []
            for index, slot in enumerate(normalized, 1):
                if moment(slot['start']) < moment(state['now']):
                    raise LedgerError('Cannot book time in the past')
                row = {'id': f'{identifier}:{index}', **slot, 'status': 'booked', 'reason': reason}
                state['reservations'].append(row)
                rows.append(row)
            self._log(state, 'reserved', reservations=[r['id'] for r in rows], reason=reason)
            return rows
        return self._operation(identifier, {'kind': 'reserve', 'slots': normalized, 'reason': reason}, apply)

    def cancel(self, identifier, reservation_id, reason):
        def apply(state):
            row = next((r for r in state['reservations'] if r['id'] == reservation_id), None)
            if row is None or row['status'] != 'booked' or moment(row['start']) <= moment(state['now']):
                raise LedgerError('Only unstarted future reservations can be cancelled')
            row['status'] = 'cancelled'
            return self._log(state, 'reservation_cancelled', reservation=reservation_id, reason=reason)
        return self._operation(identifier, {'kind': 'cancel', 'reservation': reservation_id, 'reason': reason}, apply)

    def used_minutes(self, actor, week_date):
        week = week_start(week_date).date().isoformat()
        return sum(minutes for row in self.state['reservations'] if row['actor'] == actor and row['status'] != 'cancelled'
                   for key, minutes in week_parts(row['start'], row['end']) if key == week)

    def schedule_payment(self, identifier, source, target, amount, due, reason):
        due = moment(due).isoformat()
        def apply(state):
            self._money_args(state, source, target, amount)
            if moment(due) < moment(state['now']):
                raise LedgerError('Cannot schedule a new payment in the past')
            row = {'id': identifier, 'source': source, 'target': target, 'amount': amount, 'due': due,
                   'reason': reason, 'status': 'scheduled'}
            state['payments'][identifier] = row
            self._log(state, 'payment_scheduled', payment=identifier, due=due, reason=reason)
            return row
        return self._operation(identifier, dict(kind='schedule_payment', source=source, target=target, amount=amount, due=due, reason=reason), apply)

    def advance(self, target):
        finish, current = moment(target), moment(self.state['now'])
        if finish < current:
            raise LedgerError('Calendar cannot move backwards')
        state = self.snapshot()
        points = {current, finish}
        points.update(moment(p['due']) for p in state['payments'].values() if current <= moment(p['due']) <= finish)
        points.update(moment(r['end']) for r in state['reservations'] if r['status'] == 'booked' and current <= moment(r['end']) <= finish)
        for point in sorted(points):
            state['now'] = point.isoformat()
            progress = True
            while progress:
                progress = False
                for payment in sorted(state['payments'].values(), key=lambda p: (p['due'], p['id'])):
                    if payment['status'] == 'paid' or moment(payment['due']) > point:
                        continue
                    if state['accounts'][payment['source']] < payment['amount']:
                        if payment['status'] != 'blocked':
                            payment['status'] = 'blocked'
                            self._log(state, 'payment_blocked', payment=payment['id'], reason='Insufficient funds at due time')
                        continue
                    self._transfer(state, payment['source'], payment['target'], payment['amount'], payment['reason'], payment['id'])
                    payment.update(status='paid', paid_at=state['now'])
                    progress = True
            for reservation in state['reservations']:
                if reservation['status'] == 'booked' and moment(reservation['end']) <= point:
                    reservation['status'] = 'completed'
                    self._log(state, 'time_completed', reservation=reservation['id'], actor=reservation['actor'])
        self._validate(state)
        self.state = state
        return self.snapshot()
