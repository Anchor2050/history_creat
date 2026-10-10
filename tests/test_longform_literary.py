import unittest
from copy import deepcopy
from narrative.longform.literary import ReaderMemory, LiteraryError, AXES


def chapter(number=1, text='陈岚没有答应。她把报价留到明天再看。'):
    return {'number': number, 'title': '报价', 'text': text, 'summary': '报价仍未接受。',
            'event_ids': [1], 'disclosures': [], 'thread_updates': [], 'motif_updates': [],
            'fact_review': {'supported': True, 'issues': []},
            'literary_review': {'ready': True, 'axes': {axis: {'quote': text, 'observation': 'fixture assessment', 'revision': ''} for axis in AXES}}}


class LongformLiteraryTests(unittest.TestCase):
    def test_only_published_quoted_information_enters_reader_memory(self):
        memory = ReaderMemory(); item = chapter()
        item['disclosures'] = [{'id': 'quote_status', 'kind': 'world_fact', 'statement': '陈岚尚未接受报价',
                                'sources': [1], 'quote': '陈岚没有答应。'}]
        memory.publish(item, {1})
        context = memory.context()
        self.assertEqual(context['revelations']['quote_status'][0]['statement'], '陈岚尚未接受报价')
        self.assertNotIn('author_plan', context)
        context['revelations'].clear()
        self.assertIn('quote_status', memory.context()['revelations'])

    def test_unwritten_or_future_disclosure_is_rejected_atomically(self):
        for quote, sources in [('她最终接受了。', [1]), ('陈岚没有答应。', [99])]:
            memory = ReaderMemory(); before = memory.snapshot(); item = chapter()
            item['disclosures'] = [{'id': 'future', 'kind': 'world_fact', 'statement': 'future', 'quote': quote, 'sources': sources}]
            with self.assertRaises(LiteraryError): memory.publish(item, {1})
            self.assertEqual(memory.snapshot(), before)

    def test_pending_review_and_unknown_chapter_event_cannot_publish(self):
        memory = ReaderMemory(); item = chapter()
        item['fact_review']['supported'] = False
        with self.assertRaises(LiteraryError): memory.publish(item, {1})
        item = chapter(); item['event_ids'] = [2]
        with self.assertRaises(LiteraryError): memory.publish(item, {1})
        self.assertEqual(memory.snapshot()['chapters'], [])

    def test_retry_is_idempotent_but_cannot_rewrite_published_chapter(self):
        memory = ReaderMemory(); item = chapter()
        memory.publish(item, {1}); before = memory.snapshot()
        memory.publish(deepcopy(item), {1})
        self.assertEqual(memory.snapshot(), before)
        changed = chapter(text='陈岚答应了。')
        with self.assertRaises(LiteraryError): memory.publish(changed, {1})
        with self.assertRaises(LiteraryError): memory.publish(chapter(3), {1})
        self.assertEqual(memory.snapshot(), before)

    def test_thread_continues_and_resolution_needs_a_published_source(self):
        memory = ReaderMemory(); first = chapter()
        first['thread_updates'] = [{'id': 'contract', 'action': 'open', 'description': '是否接下兼职', 'sources': [1], 'quote': '陈岚没有答应。'}]
        memory.publish(first, {1})
        self.assertEqual(memory.context()['threads']['contract']['status'], 'open')
        second = chapter(2, '陈岚拒绝了这份兼职。'); second['event_ids'] = [2]
        second['thread_updates'] = [{'id': 'contract', 'action': 'resolve', 'description': '她决定拒绝本次报价', 'sources': [2], 'quote': second['text']}]
        memory.publish(second, {1, 2})
        thread = memory.context()['threads']['contract']
        self.assertEqual(thread['status'], 'resolved')
        self.assertEqual([h['chapter'] for h in thread['history']], [1, 2])
        self.assertEqual(ReaderMemory.restore(memory.snapshot()).snapshot(), memory.snapshot())

    def test_motifs_are_rendering_memory_not_world_mutations(self):
        memory = ReaderMemory(); item = chapter()
        item['motif_updates'] = [{'id': 'tomorrow', 'description': '延后的明天', 'sources': [1], 'quote': '明天再看', 'interpretation': '暂缓决定'}]
        original = deepcopy(item)
        memory.publish(item, {1})
        motif = memory.context()['motifs']['tomorrow']
        self.assertEqual(motif['scope'], 'literary_rendering_only')
        self.assertEqual(item, original)

    def test_belief_disclosures_do_not_become_objective_truth(self):
        memory = ReaderMemory(); item = chapter(text='许航希望以后还有机会。')
        item['disclosures'] = [{'id': 'hope', 'kind': 'character_belief', 'statement': '许航希望未来可能改变', 'sources': [1], 'quote': item['text']}]
        memory.publish(item, {1})
        self.assertEqual(memory.context()['revelations']['hope'][0]['kind'], 'character_belief')

    def test_literary_critique_requires_specific_axes_and_real_quotes(self):
        memory = ReaderMemory(); item = chapter()
        item['literary_review']['axes']['care_and_agency']['quote'] = 'unwritten kindness'
        with self.assertRaises(LiteraryError): memory.publish(item, {1})
        item = chapter(); del item['literary_review']['axes']['rhythm']
        with self.assertRaises(LiteraryError): memory.publish(item, {1})

    def test_author_plans_and_forged_derived_memory_are_rejected(self):
        memory = ReaderMemory(); item = chapter(); item['author_plan'] = 'future ending'
        with self.assertRaises(LiteraryError): memory.publish(item, {1})
        memory.publish(chapter(), {1})
        snapshot = memory.snapshot(); snapshot['threads']['invented'] = {'status': 'resolved'}
        with self.assertRaises(LiteraryError): ReaderMemory.restore(snapshot)
