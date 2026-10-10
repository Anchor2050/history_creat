"""Driver-neutral task exchange, embedded in the runner's atomic checkpoint.

Receive is not world acceptance. The runner must validate/apply the response on
its transactional world copy, then save world + exchange together. This module
performs no network calls, loads no credentials, and grants no action authority.
"""
from copy import deepcopy
from hashlib import sha256
import json


class ExchangeError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ExchangeError(message)


def digest(value):
    try:
        return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    except (ValueError, TypeError):
        raise ExchangeError('Task must contain finite JSON data') from None


def text(value):
    return isinstance(value, str) and bool(value.strip())


class Exchange:
    def __init__(self, run_id):
        require(text(run_id), 'Missing run ID')
        self._state = {'version': 1, 'run_id': run_id, 'pending': None, 'history': []}

    def snapshot(self):
        return deepcopy(self._state)

    def pending(self):
        pending = self._state['pending']
        return deepcopy(pending['task']) if pending else None

    def request(self, stage, state_hash, context, instruction, output_schema):
        require(all(text(v) for v in (stage, state_hash, instruction)), 'Missing task identity/instruction')
        require(isinstance(context, dict) and isinstance(output_schema, dict), 'Context and schema must be objects')
        task = dict(protocol=1, task_id=self._state['run_id'] + ':' + str(len(self._state['history'])+1),
                    stage=stage, state_hash=state_hash, context=deepcopy(context),
                    instruction=instruction, output_schema=deepcopy(output_schema))
        task['input_hash'] = digest(task)
        existing = self._state['pending']
        if existing:
            require(existing['task'] == task, 'Unfinished task cannot be overwritten')
        else:
            self._state['pending'] = {'status': 'pending', 'task': task, 'reply': None}
        return deepcopy(task)

    def receive(self, reply, current_state_hash):
        require(isinstance(reply, dict), 'Reply must be an object')
        digest(reply)
        for record in self._state['history']:
            if record['task']['task_id'] == reply.get('task_id'):
                require(record['reply'] == reply, 'Conflicting committed reply')
                return deepcopy(record)
        pending = self._state['pending']
        require(pending is not None, 'No pending task')
        task = pending['task']
        require(current_state_hash == task['state_hash'], 'Task refers to stale world state')
        require(all(reply.get(k) == task[k] for k in ('task_id', 'input_hash', 'state_hash')), 'Reply identity mismatch')
        require(text(reply.get('driver')) and isinstance(reply.get('result'), dict), 'Missing driver or result')
        require(pending['reply'] is None or pending['reply'] == reply, 'Conflicting pending reply')
        pending['reply'] = deepcopy(reply)
        pending['status'] = 'received'
        return deepcopy(pending)

    def commit(self, task_id, before_hash, validation, after_hash):
        pending = self._state['pending']
        require(pending is not None and pending['status'] == 'received', 'Receive before committing')
        require(pending['task']['task_id'] == task_id and pending['task']['state_hash'] == before_hash, 'Commit identity mismatch')
        require(isinstance(validation, dict) and type(validation.get('accepted')) is bool and text(after_hash), 'Missing engine validation receipt')
        digest(validation)
        record = {**deepcopy(pending), 'status': 'committed', 'validation': deepcopy(validation), 'after_hash': after_hash}
        self._state['history'].append(record)
        self._state['pending'] = None
        return deepcopy(record)

    @classmethod
    def restore(cls, snapshot):
        require(isinstance(snapshot, dict) and snapshot.get('version') == 1, 'Unsupported exchange snapshot')
        require(isinstance(snapshot.get('history'), list), 'Missing exchange history')
        restored = cls(snapshot.get('run_id'))
        try:
            for record in snapshot['history']:
                task = record['task']
                restored.request(task['stage'], task['state_hash'], task['context'], task['instruction'], task['output_schema'])
                require(restored.pending() == task, 'Task hash mismatch')
                restored.receive(record['reply'], task['state_hash'])
                restored.commit(task['task_id'], task['state_hash'], record['validation'], record['after_hash'])
            pending = snapshot.get('pending')
            if pending is not None:
                task = pending['task']
                restored.request(task['stage'], task['state_hash'], task['context'], task['instruction'], task['output_schema'])
                require(restored.pending() == task, 'Task hash mismatch')
                if pending['reply'] is not None:
                    restored.receive(pending['reply'], task['state_hash'])
            require(restored.snapshot() == snapshot, 'Exchange history mismatch')
        except (KeyError, TypeError):
            raise ExchangeError('Malformed exchange snapshot') from None
        return restored
