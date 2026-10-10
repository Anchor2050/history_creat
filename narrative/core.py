"""Transactional world state, private beliefs, institutions and causal history."""
from copy import deepcopy
import hashlib
import json
from .rules import condition, validate_condition, permitted


class InvalidAction(ValueError):
    pass


SCHEMA = {
    'wait': set(), 'move': {'target'}, 'transfer': {'target', 'item'},
    'tell': {'target', 'fact'}, 'send': {'target', 'fact', 'delay'},
    'speak': {'target', 'text'}, 'investigate': {'fact'},
    'promise': {'target', 'item', 'due_in'},
    'allocate': {'org', 'resource', 'amount', 'target'},
    'request': {'org', 'resource', 'amount'}, 'enact': {'org', 'policy', 'value'}, 'perform': {'rule'}
}


class World:
    def __init__(self, scenario):
        self.state = deepcopy(scenario)
        s = self.state
        for key, default in {'tick': 0, 'promises': [], 'messages': [], 'organizations': {},
                             'rules': {}, 'flags': {}, 'items': {}, 'facts': {}, 'requests': []}.items():
            s.setdefault(key, deepcopy(default))
        for actor in s.get('actors', {}).values():
            for key, default in {'beliefs': [], 'claims': {}, 'resources': {}, 'relationships': {},
                                 'reflections': [], 'experiences': [], 'goals': []}.items():
                actor.setdefault(key, deepcopy(default))
            for fact in actor['beliefs']:
                actor['claims'].setdefault(fact, {'value': True, 'source': 'initial', 'event': None})
            for goal in actor['goals']:
                if isinstance(goal, dict):
                    goal.setdefault('status', 'active')
        self.events = []
        self.lineage = {}
        self.runtime = {'next_actor': 0, 'attempts': 0}
        self._validate()
        self.initial = deepcopy(self.state)

    def _validate(self):
        s = self.state
        if not s.get('locations') or not s.get('actors') or len(set(s['locations'])) != len(s['locations']):
            raise ValueError('World needs unique locations and actors')
        if type(s['tick']) is not int or s['tick'] < 0:
            raise ValueError('Invalid tick')
        for route in s.get('routes', []):
            if len(route) != 2 or any(p not in s['locations'] for p in route):
                raise ValueError('Invalid route')
        for actor in s['actors'].values():
            if actor['location'] not in s['locations']:
                raise ValueError('Unknown location')
            for fact, claim in actor['claims'].items():
                if fact not in s['facts'] or type(claim.get('value')) is not bool:
                    raise ValueError('Invalid claim')
            self._resources(actor['resources'])
            for goal in actor['goals']:
                if isinstance(goal, dict):
                    validate_condition(s, goal['condition'])
                    if 'deadline' in goal and (type(goal['deadline']) is not int or goal['deadline'] < 0):
                        raise ValueError('Invalid goal deadline')
        if any(owner not in s['actors'] for owner in s['items'].values()):
            raise ValueError('Unknown owner')
        for fact in s['facts'].values():
            if not isinstance(fact, (str, dict)):
                raise ValueError('Invalid fact')
            if isinstance(fact, dict) and (not isinstance(fact.get('text'), str) or type(fact.get('truth', True)) is not bool or fact.get('location') not in s['locations']):
                raise ValueError('Invalid investigable fact')
        for org in s['organizations'].values():
            if any(n not in s['actors'] for n in org['members']):
                raise ValueError('Unknown organization member')
            self._resources(org.get('resources', {}))
            for policy, value in org.get('policies', {}).items():
                if value not in org.get('policy_options', {}).get(policy, []):
                    raise ValueError('Unknown policy option')
        for rule in s['rules'].values():
            if set(rule) - {'description', 'location', 'cost', 'requires', 'effects', 'org', 'permission', 'once'}:
                raise ValueError('Unknown rule field')
            if rule.get('location') not in s['locations']:
                raise ValueError('Invalid rule location')
            self._resources(rule.get('cost', {}))
            for spec in rule.get('requires', []):
                validate_condition(s, spec)
            effects = rule.get('effects', {})
            if set(effects) - {'flags', 'resources', 'reveal'}:
                raise ValueError('Unknown rule effect')
            self._resources(effects.get('resources', {}))
            if any(f not in s['facts'] for f in effects.get('reveal', [])):
                raise ValueError('Unknown revealed fact')
            if 'org' in rule and rule['org'] not in s['organizations']:
                raise ValueError('Unknown rule organization')

    @staticmethod
    def _resources(resources):
        if not isinstance(resources, dict) or any(type(v) is not int or v < 0 for v in resources.values()):
            raise ValueError('Resources must be nonnegative integers')

    def snapshot(self):
        return deepcopy({'version': 2, 'state': self.state, 'events': self.events, 'branch': self.lineage, 'runtime': self.runtime, 'initial': self.initial})

    @classmethod
    def restore(cls, snapshot):
        if snapshot.get('version') not in (1, 2):
            raise ValueError('Unsupported snapshot version')
        world = cls(snapshot['state'])
        world.events = deepcopy(snapshot['events'])
        world.lineage = deepcopy(snapshot.get('branch', {}))
        world.runtime = deepcopy(snapshot.get('runtime', {'next_actor': world.state['tick'], 'attempts': world.state['tick']}))
        if [e['id'] for e in world.events] != list(range(1, len(world.events) + 1)) or world.state['tick'] != len(world.events):
            raise ValueError('Invalid event sequence/time')
        if 'initial' in snapshot:
            world.initial = deepcopy(snapshot['initial'])
        else:
            world.initial = deepcopy(world.state)
            for event in reversed(world.events):
                for key, change in event['changes'].items():
                    world.initial[key] = deepcopy(change['before'])
            for actor in world.initial['actors'].values():
                actor['reflections'] = []
        return world

    def branch(self, label):
        snapshot = self.snapshot()
        child = self.restore(snapshot)
        child.lineage = {'label': label, 'parent_tick': self.state['tick'],
                         'parent_sha256': hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()}
        return child

    def _visible(self, name):
        return {e['id'] for e in self.events if name in e['audience'] or name in e.get('notices', {})}

    def _belief_text(self, fact, value):
        data = self.state['facts'][fact]
        text = data if isinstance(data, str) else data['text']
        return text if value else (data.get('false_text', 'NOT: ' + text) if isinstance(data, dict) else 'NOT: ' + text)

    def view(self, name):
        s = self.state
        actor = s['actors'][name]
        visible = self._visible(name)
        events = []
        for e in self.events:
            if e['id'] in visible:
                events.append({'id': e['id'], 'tick': e['tick'],
                               'action': e['action'] if name in e['audience'] else {'kind': 'notice'},
                               'causes': [i for i in e['causes'] if i in visible],
                               'notices': e.get('notices', {}).get(name, [])})
        return deepcopy({
            'tick': s['tick'], 'self': dict(actor, id=name),
            'public_context': s.get('public_context', ''),
            'public_rules': {r: {'description': spec['description'], 'location': spec['location'], 'cost': spec.get('cost', {})} for r, spec in s['rules'].items()},
            'nearby': {n: {'location': a['location']} for n, a in s['actors'].items() if n != name and a['location'] == actor['location']},
            'destinations': sorted({p for r in s.get('routes', []) if actor['location'] in r for p in r if p != actor['location']}),
            'inventory': [i for i, owner in s['items'].items() if owner == name],
            'beliefs': {f: {'statement': self._belief_text(f, c['value']), 'source': c['source']} for f, c in actor['claims'].items()},
            'promises': [p for p in s['promises'] if name in (p['actor'], p['target'])],
            'organizations': {o: g for o, g in s['organizations'].items() if name in g['members']},
            'requests': [r for r in s['requests'] if name in s['organizations'][r['org']]['members']],
            'flags': s['flags'], 'experiences': actor['experiences'], 'events': events,
            'opportunities': {r: spec['description'] for r, spec in s['rules'].items() if spec['location'] == actor['location']}
        })

    def reflect(self, name, text, evidence):
        if not isinstance(text, str) or not text.strip() or len(text) > 1200 or not isinstance(evidence, list) or not evidence or any(type(i) is not int or i not in self._visible(name) for i in evidence):
            raise InvalidAction('Reflection needs observed event evidence and a short text')
        self.state['actors'][name]['reflections'].append({'text': text, 'events': list(evidence), 'tick': self.state['tick']})

    def _claim(self, s, target, fact, value, source, event):
        s['actors'][target]['claims'][fact] = {'value': value, 'source': source, 'event': event}
        if fact not in s['actors'][target]['beliefs']:
            s['actors'][target]['beliefs'].append(fact)

    def _rule_ok(self, s, name, rule_id):
        r = s['rules'].get(rule_id)
        if not r or r['location'] != s['actors'][name]['location']:
            return False
        if r.get('once') and s['flags'].get('used:' + rule_id):
            return False
        if 'org' in r and not permitted(s, name, r['org'], r.get('permission', 'perform')):
            return False
        return all(s['actors'][name]['resources'].get(k, 0) >= v for k, v in r.get('cost', {}).items()) and all(condition(s, name, p) for p in r.get('requires', []))

    def actions(self, name):
        """Finite, grounded candidates; models may also supply speak text separately."""
        v, s = self.view(name), self.state
        out = [{'actor': name, 'kind': 'wait'}]
        out += [{'actor': name, 'kind': 'move', 'target': p} for p in v['destinations']]
        for target in v['nearby']:
            out += [{'actor': name, 'kind': 'transfer', 'target': target, 'item': i} for i in v['inventory']]
            out += [{'actor': name, 'kind': 'promise', 'target': target, 'item': i, 'due_in': 3} for i in v['inventory']]
            out += [{'actor': name, 'kind': 'tell', 'target': target, 'fact': f} for f in v['beliefs']]
        # All actor identities are public in the scenario; remote private state is not.
        for target in s['actors']:
            if target != name and target not in v['nearby']:
                out += [{'actor': name, 'kind': 'send', 'target': target, 'fact': f, 'delay': 2} for f in v['beliefs']]
        for f, spec in s['facts'].items():
            if isinstance(spec, dict) and spec['location'] == v['self']['location']:
                out.append({'actor': name, 'kind': 'investigate', 'fact': f})
        for org, group in v['organizations'].items():
            for resource, count in group.get('resources', {}).items():
                for amount in sorted(set(range(1, min(max(count, 2), 10) + 1)) | {max(1, count)}):
                    if not any(r['actor'] == name and r['org'] == org and r['resource'] == resource and r['status'] == 'open' for r in s['requests']):
                        out.append({'actor': name, 'kind': 'request', 'org': org, 'resource': resource, 'amount': amount})
            if permitted(s, name, org, 'allocate'):
                for resource, count in group.get('resources', {}).items():
                    for target in group['members']:
                        for amount in sorted(set(range(1, min(count, 10) + 1)) | {count}):
                            caps = [opts.get(group['policies'].get(policy), count) for policy, opts in group.get('allocation_limits', {}).items()]
                            if min([count] + caps) >= amount > 0:
                                out.append({'actor': name, 'kind': 'allocate', 'org': org, 'resource': resource, 'amount': amount, 'target': target})
            if permitted(s, name, org, 'enact'):
                for policy, options in group.get('policy_options', {}).items():
                    out += [{'actor': name, 'kind': 'enact', 'org': org, 'policy': policy, 'value': val} for val in options if val != group['policies'].get(policy)]
        out += [{'actor': name, 'kind': 'perform', 'rule': r} for r in s['rules'] if self._rule_ok(s, name, r)]
        return out

    def act(self, action, intention=None):
        if intention is not None and (not isinstance(intention, str) or len(intention) > 1200):
            raise InvalidAction("Intention must be a short self-report")
        if not isinstance(action, dict) or not isinstance(action.get('kind'), str) or action['kind'] not in SCHEMA or not isinstance(action.get('actor'), str) or action['actor'] not in self.state['actors']:
            raise InvalidAction('Unknown actor or action')
        a = deepcopy(action)
        name, kind = a['actor'], a['kind']
        required = {'actor', 'kind'} | SCHEMA[kind]
        if set(a) - (required | {'causes'}) or required - set(a):
            raise InvalidAction('Missing or inappropriate action fields')
        for field in SCHEMA[kind] - {'amount', 'delay', 'due_in', 'value'}:
            if not isinstance(a[field], str):
                raise InvalidAction('Action identifiers and text must be strings')
        causes = a.get('causes', [])
        if not isinstance(causes, list) or any(type(c) is not int or c not in self._visible(name) for c in causes):
            raise InvalidAction('Causes must reference observed earlier events')
        s = deepcopy(self.state)
        actor, target = s['actors'][name], a.get('target')
        eid = len(self.events) + 1
        audience, notices, extra_deps = [name], {}, []
        reads = {'actors/' + name}
        if kind in {'transfer', 'tell', 'promise', 'speak', 'send'}:
            if target == name or target not in s['actors']:
                raise InvalidAction('Invalid counterpart')
            reads.add('actors/' + target)
            if kind != 'send':
                if s['actors'][target]['location'] != actor['location']:
                    raise InvalidAction('Counterpart must be at the same location')
                audience.append(target)
        if kind == 'move':
            if target not in self.view(name)['destinations']:
                raise InvalidAction('No direct route')
            actor['location'] = target
        elif kind == 'transfer':
            reads.add('items/' + a['item'])
            if s['items'].get(a['item']) != name:
                raise InvalidAction('Actor does not own the item')
            s['items'][a['item']] = target
            for p in s['promises']:
                if p['status'] == 'pending' and (p['actor'], p['target'], p['item']) == (name, target, a['item']):
                    p['status'] = 'fulfilled'
                    extra_deps.append(p.get('event', 0))
                    self._experience(s, p['target'], name, 1, 'promise fulfilled', eid)
        elif kind in {'tell', 'send'}:
            if a['fact'] not in actor['claims']:
                raise InvalidAction('Actor cannot transmit an unknown claim')
            claim = actor['claims'][a['fact']]
            if claim.get('event'):
                extra_deps.append(claim['event'])
            if kind == 'tell':
                self._claim(s, target, a['fact'], claim['value'], name, eid)
            else:
                if type(a['delay']) is not int or not 1 <= a['delay'] <= 100:
                    raise InvalidAction('Message delay must be 1..100')
                s['messages'].append({'source': name, 'target': target, 'fact': a['fact'], 'value': claim['value'], 'due': s['tick'] + 1 + a['delay'], 'event': eid})
        elif kind == 'speak':
            if not 1 <= len(a['text']) <= 600:
                raise InvalidAction('Dialogue must be 1..600 characters')
        elif kind == 'investigate':
            fact = s['facts'].get(a['fact'])
            if not isinstance(fact, dict) or fact['location'] != actor['location']:
                raise InvalidAction('Evidence is not accessible here')
            self._claim(s, name, a['fact'], fact.get('truth', True), 'investigation', eid)
        elif kind == 'promise':
            if a['item'] not in s['items'] or type(a['due_in']) is not int or not 1 <= a['due_in'] <= 100:
                raise InvalidAction('Promise needs an existing item and bounded positive deadline')
            s['promises'].append({'id': len(s['promises']) + 1, 'actor': name, 'target': target, 'item': a['item'], 'due': s['tick'] + 1 + a['due_in'], 'status': 'pending', 'event': eid})
        elif kind == 'request':
            org = s['organizations'].get(a['org'], {})
            if name not in org.get('members', {}) or a['resource'] not in org.get('resources', {}) or type(a['amount']) is not int or a['amount'] < 1:
                raise InvalidAction('Invalid resource request')
            if any(r['actor'] == name and r['org'] == a['org'] and r['resource'] == a['resource'] and r['status'] == 'open' for r in s['requests']):
                raise InvalidAction('An equivalent request is already pending')
            s['requests'].append({'id': len(s['requests']) + 1, 'actor': name, 'org': a['org'], 'resource': a['resource'], 'remaining': a['amount'], 'status': 'open', 'event': eid})
            audience = list(org['members'])
        elif kind in {'allocate', 'enact'}:
            org = a['org']
            reads.add('organizations/' + org)
            if not permitted(s, name, org, kind):
                raise InvalidAction('Organization permission denied')
            group = s['organizations'][org]
            if kind == 'allocate':
                amount = a['amount']
                if target not in group['members'] or type(amount) is not int or amount < 1 or group.get('resources', {}).get(a['resource'], 0) < amount:
                    raise InvalidAction('Invalid allocation or insufficient resource')
                if any(amount > options.get(group['policies'].get(policy), amount) for policy, options in group.get('allocation_limits', {}).items()):
                    raise InvalidAction('Allocation exceeds current policy limit')
                group['resources'][a['resource']] -= amount
                dest = s['actors'][target]['resources']
                dest[a['resource']] = dest.get(a['resource'], 0) + amount
                available = amount
                for request in s['requests']:
                    if request['status'] == 'open' and request['actor'] == target and request['org'] == org and request['resource'] == a['resource']:
                        credited = min(available, request['remaining'])
                        request['remaining'] -= credited
                        available -= credited
                        extra_deps.append(request['event'])
                        if request['remaining'] == 0:
                            request['status'] = 'fulfilled'
            else:
                if a['value'] not in group.get('policy_options', {}).get(a['policy'], []):
                    raise InvalidAction('Invalid policy value')
                group['policies'][a['policy']] = a['value']
            audience = list(group['members'])
        elif kind == 'perform':
            if not self._rule_ok(s, name, a['rule']):
                raise InvalidAction('Rule conditions or costs not satisfied')
            r = s['rules'][a['rule']]
            reads.update('flags/' + f for f in s['flags'])
            if 'org' in r:
                reads.add('organizations/' + r['org'])
            reads.update('organizations/' + p['org'] for p in r.get('requires', []) if p['kind'] == 'policy')
            for k, value in r.get('cost', {}).items():
                actor['resources'][k] -= value
            effects = r.get('effects', {})
            s['flags'].update(effects.get('flags', {}))
            for k, value in effects.get('resources', {}).items():
                actor['resources'][k] = actor['resources'].get(k, 0) + value
            for fact in effects.get('reveal', []):
                value = s['facts'][fact]
                self._claim(s, name, fact, value.get('truth', True) if isinstance(value, dict) else True, 'rule:' + a['rule'], eid)
            if r.get('once'):
                s['flags']['used:' + a['rule']] = True
        s['tick'] += 1
        for message in list(s['messages']):
            if s['tick'] >= message['due']:
                self._claim(s, message['target'], message['fact'], message['value'], message['source'], eid)
                notices.setdefault(message['target'], []).append({'kind': 'message_arrived', 'from': message['source'], 'fact': message['fact']})
                extra_deps.append(message['event'])
                s['messages'].remove(message)
        for p in s['promises']:
            if p['status'] == 'pending' and s['tick'] >= p['due']:
                p['status'] = 'broken'
                extra_deps.append(p.get('event', 0))
                self._experience(s, p['target'], p['actor'], -1, 'promise broken', eid)
                for who in (p['actor'], p['target']):
                    notices.setdefault(who, []).append({'kind': 'promise_broken', 'promise': p['id']})
        for who, person in s['actors'].items():
            for goal in person['goals']:
                if isinstance(goal, dict) and goal['status'] == 'active':
                    if condition(s, who, goal['condition']):
                        goal['status'] = 'achieved'
                    elif 'deadline' in goal and s['tick'] >= goal['deadline']:
                        goal['status'] = 'failed'
                    if goal['status'] != 'active':
                        goal['event'] = eid
                        notices.setdefault(who, []).append({'kind': 'goal_' + goal['status'], 'goal': goal['id']})
        changes = {k: {'before': deepcopy(self.state.get(k)), 'after': deepcopy(v)} for k, v in s.items() if self.state.get(k) != v}
        writes = set()
        for key in changes:
            if isinstance(s[key], dict):
                writes.update(key + '/' + str(k) for k in s[key] if self.state.get(key, {}).get(k) != s[key][k])
            else:
                writes.add(key)
        last_writers = {}
        for e in self.events:
            for path in e.get('writes', []):
                last_writers[path] = e['id']
        dependencies = sorted({last_writers[p] for p in reads | writes if p in last_writers and p != 'tick'} | {i for i in extra_deps if i})
        event = {'id': eid, 'tick': s['tick'], 'action': a, 'causes': causes, 'dependencies': dependencies,
                 'audience': audience, 'notices': notices, 'changes': changes, 'writes': sorted(writes), 'intention': intention}
        self.state = s
        self.events.append(deepcopy(event))
        return deepcopy(event)

    @staticmethod
    def _experience(s, who, other, delta, description, eid):
        actor = s['actors'][who]
        relation = actor['relationships'].setdefault(other, {'trust': 0})
        relation['trust'] = max(-5, min(5, relation['trust'] + delta))
        actor['experiences'].append({'event': eid, 'other': other, 'description': description})
