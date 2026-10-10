"""Standalone bounded DeepSeek pipeline; no Codex/GPT service or human gate."""
import argparse
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

from .providers import DeepSeek, ProviderError
from .core import InvalidAction
from .run import DEMO, run, load_world, export, save_json
from .story import create_story, render_story


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save_story(folder, story):
    save_json(folder / 'story-draft.json', story)
    (folder / 'story-draft.md').write_text(render_story(story), encoding='utf-8')


def activity_report(world, output):
    statuses = Counter()
    attempts = Path(output) / 'attempts.jsonl'
    if attempts.exists():
        for line in attempts.read_text(encoding='utf-8').splitlines():
            if line.strip():
                statuses[json.loads(line)['status']] += 1
    repeated = 0
    last_by_actor = {}
    for event in world.events:
        action = {key: value for key, value in event['action'].items() if key != 'causes'}
        actor = action['actor']
        repeated += last_by_actor.get(actor) == action
        last_by_actor[actor] = action
    return {'committed_events': len(world.events), 'attempt_statuses': dict(statuses),
            'wait_actions': sum(e['action']['kind'] == 'wait' for e in world.events),
            'no_change_beyond_time': sum(not (set(e['changes']) - {'tick'}) for e in world.events),
            'repeated_same_actor_actions': repeated,
            'note': 'These are activity indicators, not a literary quality score. Waiting and repetition may be intentional.'}


def run_job(*, output, scenario=DEMO, rounds=3, steps_per_round=6, max_calls=80,
            max_revisions=2, resume=False, client=None, retries=2,
            thinking=True, max_output_tokens=8192, max_output_ceiling=32768):
    if max_output_tokens < 1 or max_output_ceiling < max_output_tokens:
        raise ValueError('Output ceiling must be at least the initial output limit')
    if min(rounds, steps_per_round, max_calls) < 1 or min(max_revisions, retries) < 0:
        raise ValueError('Invalid job bounds')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    job_path = output / 'job.json'
    checkpoint = output / 'checkpoint.json'
    if resume:
        job = read_json(job_path)
        if job['status'] == 'completed':
            return job
    else:
        if job_path.exists() or checkpoint.exists():
            raise ValueError('Existing job: use --resume or another output directory')
        world = load_world(scenario)
        export(world, output)
        job = {'version': 1, 'status': 'running', 'round': 0, 'stage': 'actions',
               'rounds': rounds, 'steps_per_round': steps_per_round, 'max_revisions': max_revisions,
               'round_start_attempts': 0, 'reflection_cursor': 0, 'results': [], 'errors': []}
        save_json(job_path, job)
    client = client or DeepSeek(max_calls=max_calls, thinking=thinking, max_output_tokens=max_output_tokens)
    client.max_output_tokens = min(max_output_ceiling, max(client.max_output_tokens, job.get('output_token_limit', 0)))
    job['output_token_limit'] = client.max_output_tokens
    call_start, token_start = client.calls, client.total_tokens
    failures = 0
    job['status'] = 'running'
    save_json(job_path, job)
    try:
        while job['round'] < job['rounds']:
            try:
                world = load_world(checkpoint, resume=True)
                if job['stage'] == 'actions':
                    remaining = job['steps_per_round'] - (world.runtime['attempts'] - job['round_start_attempts'])
                    if remaining > 0:
                        world = run(output=output, resume=checkpoint, steps=remaining, live=True, client=client,
                                    max_calls=client.max_calls)
                    job['stage'] = 'reflection'
                    job['reflection_cursor'] = 0
                elif job['stage'] == 'reflection':
                    names = list(world.state['actors'])
                    index = job['reflection_cursor']
                    if index < len(names):
                        name = names[index]
                        view = world.view(name)
                        old = world.state['actors'][name]['reflections']
                        # If interrupted between world save and job save, this reflection is already durable.
                        if view['events'] and not (old and old[-1]['tick'] == world.state['tick']):
                            result = client.json(
                                'Reflect as this character on observed outcomes, conflicting goals and relationships. '
                                'State a concrete next intention or reconsideration in Chinese, not imaginary achievements. '
                                'Return {"text":"under 150 Chinese characters","evidence":[observed_event_ids]}.', view)
                            try:
                                world.reflect(name, result.get('text'), result.get('evidence'))
                            except InvalidAction:
                                raise ProviderError('Invalid character reflection') from None
                            export(world, output)
                        job['reflection_cursor'] += 1
                    else:
                        job['stage'] = 'story'
                elif job['stage'] == 'story':
                    folder = output / f"round-{job['round'] + 1:04d}"
                    folder.mkdir(exist_ok=True)
                    progress_path = folder / 'story-progress.json'
                    if world.events:
                        story = create_story(world, client, max_revisions=job['max_revisions'],
                                             checkpoint=read_json(progress_path) if progress_path.exists() else None,
                                             progress=lambda record: save_json(progress_path, record))
                        save_story(folder, story)
                        status = story['status']
                    else:
                        status = 'no_committed_history'
                    job['results'].append({'round': job['round'] + 1, 'events_total': len(world.events),
                                           'story_status': status, 'actions': dict(Counter(e['action']['kind'] for e in world.events))})
                    job['round'] += 1
                    job['stage'] = 'actions'
                    job['round_start_attempts'] = world.runtime['attempts']
                else:
                    raise ValueError('Unknown saved job stage')
                failures = 0
                save_json(job_path, job)
            except ProviderError as exc:
                job['errors'].append({'round': job['round'] + 1, 'stage': job['stage'], 'reason': str(exc)})
                if str(exc) == 'Incomplete generation: length' and client.max_output_tokens < max_output_ceiling:
                    client.max_output_tokens = min(max_output_ceiling, client.max_output_tokens * 2)
                    job['output_token_limit'] = client.max_output_tokens
                    job['errors'][-1]['next_output_token_limit'] = client.max_output_tokens
                failures += 1
                if client.calls >= client.max_calls:
                    job['status'] = 'budget_exhausted'
                elif failures > retries:
                    job['status'] = 'failed'
                save_json(job_path, job)
                if job['status'] != 'running':
                    break
        if job['round'] == job['rounds']:
            job['status'] = 'completed'
            save_json(job_path, job)
    finally:
        usage = {'model': client.model, 'thinking': getattr(client, 'thinking', None),
                 'calls': client.calls - call_start, 'tokens_reported': client.total_tokens - token_start,
                 'max_calls_this_invocation': client.max_calls, 'final_output_token_limit': client.max_output_tokens, 'status': job['status'],
                 'diagnostics': getattr(client, 'diagnostics', [])}
        with (output / 'job-usage.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(usage, ensure_ascii=False) + '\n')
        save_json(output / 'job-report.json', {'status': job['status'], 'results': job['results'], 'errors': job['errors'],
                                             'activity': activity_report(load_world(checkpoint, resume=True), output),
                                             'note': 'completed means configured rounds finished, not literary quality certified.'})
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', type=Path, default=DEMO)
    parser.add_argument('--output', type=Path, default=Path('output') / ('auto-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f')))
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--steps-per-round', type=int, default=6)
    parser.add_argument('--max-calls', type=int, default=80)
    parser.add_argument('--max-revisions', type=int, default=2)
    parser.add_argument('--retries', type=int, default=2)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--thinking', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--max-output-tokens', type=int, default=8192)
    parser.add_argument('--max-output-ceiling', type=int, default=32768)
    args = parser.parse_args()
    try:
        job = run_job(**vars(args))
    except (ValueError, OSError, ProviderError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(f"{job['status']}: {args.output.resolve()}")
    if job['status'] != 'completed':
        parser.exit(2)


if __name__ == '__main__':
    main()
