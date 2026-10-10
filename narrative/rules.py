"""Declarative predicates and effects shared by different fictional worlds."""


def condition(state, actor, spec):
    person = state['actors'][actor]
    kind = spec.get('kind')
    if kind == 'resource':
        return person['resources'].get(spec['resource'], 0) >= spec['at_least']
    if kind == 'item':
        return state['items'].get(spec['item']) == actor
    if kind == 'knows':
        claim = person['claims'].get(spec['fact'])
        return claim is not None and claim['value'] == spec.get('value', True)
    if kind == 'flag':
        return state['flags'].get(spec['flag']) == spec['value']
    if kind == 'policy':
        return state['organizations'][spec['org']]['policies'].get(spec['policy']) == spec['value']
    if kind == 'location':
        return person['location'] == spec['location']
    raise ValueError('Unknown condition kind')


def validate_condition(state, spec):
    fields = {'resource': {'resource', 'at_least'}, 'item': {'item'}, 'knows': {'fact'},
              'flag': {'flag', 'value'}, 'policy': {'org', 'policy', 'value'}, 'location': {'location'}}
    kind = spec.get('kind')
    if kind not in fields or not fields[kind] <= spec.keys():
        raise ValueError('Invalid condition')
    if kind == 'knows' and (spec['fact'] not in state['facts'] or type(spec.get('value', True)) is not bool):
        raise ValueError('Invalid fact condition')
    if kind == 'item' and spec['item'] not in state['items']:
        raise ValueError('Unknown item condition')
    if kind == 'policy' and spec['org'] not in state['organizations']:
        raise ValueError('Unknown organization condition')
    if kind == 'location' and spec['location'] not in state['locations']:
        raise ValueError('Unknown location condition')
    if kind == 'resource' and (type(spec['at_least']) is not int or spec['at_least'] < 0):
        raise ValueError('Invalid resource condition')


def permitted(state, actor, org, operation):
    group = state['organizations'].get(org, {})
    role = group.get('members', {}).get(actor)
    return role is not None and role in group.get('permissions', {}).get(operation, [])
