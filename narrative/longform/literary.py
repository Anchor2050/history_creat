"""Published reader knowledge. Literary metadata never mutates the world.

Quotes and source IDs provide traceability, not semantic proof. Review quality
remains an empirical property of the reviewing driver.
"""
from copy import deepcopy

AXES = ('voice', 'concreteness', 'rhythm', 'care_and_agency', 'motifs')


class LiteraryError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise LiteraryError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


class ReaderMemory:
    def __init__(self):
        self._state = {'version': 1, 'chapters': [], 'revelations': {}, 'threads': {}, 'motifs': {}}

    def snapshot(self):
        return deepcopy(self._state)

    @classmethod
    def restore(cls, snapshot):
        require(isinstance(snapshot, dict) and snapshot.get('version') == 1, 'Unsupported memory snapshot')
        restored = cls()
        require(isinstance(snapshot.get('chapters'), list), 'Missing published chapters')
        for record in snapshot['chapters']:
            require(isinstance(record, dict) and 'chapter' in record and 'available_event_ids' in record, 'Invalid chapter record')
            restored.publish(record['chapter'], record['available_event_ids'])
        require(restored.snapshot() == snapshot, 'Reader memory differs from published evidence')
        return restored

    def context(self, recent_chapters=2):
        require(type(recent_chapters) is int and recent_chapters >= 0, 'Invalid context window')
        state = self.snapshot()
        chapters = [r['chapter'] for r in state.pop('chapters')]
        state['chapter_summaries'] = [{key: c[key] for key in ('number', 'title', 'summary')} for c in chapters]
        state['recent_chapters'] = chapters[-recent_chapters:] if recent_chapters else []
        return state

    def publish(self, chapter, available_event_ids):
        require(isinstance(chapter, dict), 'Chapter must be an object')
        allowed = {'number', 'title', 'text', 'summary', 'event_ids', 'disclosures', 'thread_updates', 'motif_updates', 'fact_review', 'literary_review'}
        require(set(chapter) == allowed, 'Unexpected or missing chapter fields')
        number = chapter.get('number')
        require(type(number) is int and number > 0, 'Invalid chapter number')
        available = list(available_event_ids)
        require(all(type(i) is int and i > 0 for i in available), 'Invalid available event IDs')
        available = sorted(set(available))
        records = self._state['chapters']
        if number <= len(records):
            require(records[number-1]['chapter'] == chapter, 'Published chapter cannot be rewritten')
            require(set(chapter['event_ids']) <= set(available), 'Published sources unavailable')
            return deepcopy(records[number-1])
        require(number == len(records)+1, 'Chapters must be consecutive')
        for field in ('title', 'text', 'summary'):
            require(nonempty(chapter.get(field)), 'Missing ' + field)
        events = chapter.get('event_ids')
        require(isinstance(events, list) and all(type(i) is int and i > 0 for i in events), 'Invalid chapter events')
        require(len(set(events)) == len(events) and set(events) <= set(available), 'Unknown or duplicate chapter events')
        text = chapter['text']
        fact = chapter.get('fact_review', {})
        require(isinstance(fact, dict) and fact.get('supported') is True and fact.get('issues') == [], 'Fact review not passed')
        literary = chapter.get('literary_review', {})
        require(isinstance(literary, dict) and literary.get('ready') is True, 'Literary review not passed')
        axes = literary.get('axes', {})
        require(isinstance(axes, dict) and set(axes) == set(AXES), 'Literary review axes incomplete')
        for assessment in axes.values():
            require(isinstance(assessment, dict), 'Invalid literary assessment')
            quote = assessment.get('quote')
            # Empty evidence may explicitly diagnose absence; never invent kindness.
            require(isinstance(quote, str) and quote in text, 'Literary quote absent from text')
            require(nonempty(assessment.get('observation')) and isinstance(assessment.get('revision'), str), 'Missing literary assessment')
        state = self.snapshot()
        for category in ('disclosures', 'thread_updates', 'motif_updates'):
            updates = chapter.get(category)
            require(isinstance(updates, list), 'Missing ' + category)
            seen = set()
            for update in updates:
                require(isinstance(update, dict) and nonempty(update.get('id')), 'Missing update ID')
                identity = update['id']
                require(identity not in seen, 'Duplicate update ID')
                seen.add(identity)
                quote = update.get('quote')
                require(nonempty(quote) and quote in text, 'Memory quote absent from published text')
                sources = update.get('sources')
                require(isinstance(sources, list) and bool(sources), 'Missing update sources')
                require(all((type(i) is int and i in events) or i == 'initial' for i in sources), 'Unknown update source')
                entry = deepcopy(update)
                entry['chapter'] = number
                if category == 'disclosures':
                    require(update.get('kind') in ('world_fact', 'character_belief', 'uncertain'), 'Invalid disclosure kind')
                    require(nonempty(update.get('statement')), 'Missing disclosure statement')
                    state['revelations'].setdefault(identity, []).append(entry)
                elif category == 'thread_updates':
                    require(nonempty(update.get('description')), 'Missing thread description')
                    action = update.get('action')
                    old = state['threads'].get(identity)
                    if action == 'open':
                        require(old is None, 'Thread already exists')
                        old = {'status': 'open', 'history': []}
                        state['threads'][identity] = old
                    elif action == 'reopen':
                        require(old is not None and old['status'] in ('resolved', 'abandoned'), 'Thread cannot reopen')
                    else:
                        require(action in ('develop', 'resolve', 'abandon') and old is not None and old['status'] == 'open', 'Invalid thread transition')
                    old['status'] = {'resolve': 'resolved', 'abandon': 'abandoned'}.get(action, 'open')
                    old['history'].append(entry)
                else:
                    require(nonempty(update.get('description')) and nonempty(update.get('interpretation')), 'Missing motif interpretation')
                    motif = state['motifs'].setdefault(identity, {'scope': 'literary_rendering_only', 'history': []})
                    motif['history'].append(entry)
        record = {'chapter': deepcopy(chapter), 'available_event_ids': available}
        state['chapters'].append(record)
        self._state = state
        return deepcopy(record)
