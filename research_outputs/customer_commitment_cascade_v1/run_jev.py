"""Run frozen C01 Noul questions; persist responses without labels or secrets."""
import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

out = Path(__file__).resolve().parent
load_dotenv(out.parents[1] / '.env')
read = lambda name: json.loads((out / name).read_text(encoding='utf-8'))
write = lambda name, value: (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
url = 'https://api.typesafe.ai/v1/systemone'
model = 'jev-1.13.0'


def frozen():
    manifest = read('benchmark_manifest.json')
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Frozen file changed: {name}')
    if manifest['api']['url'] != url or manifest['api']['model'] != model:
        raise RuntimeError('Frozen endpoint or model changed')
    if manifest['routing'] != {'YES_at_least': .70, 'NO_at_most': .30, 'otherwise': 'fresh independent Luna Max fallback'}:
        raise RuntimeError('Frozen cascade routing changed')
    rows = read('benchmark.json')['examples']
    if [r['example_id'] for r in rows] != manifest['example_ids']:
        raise RuntimeError('Frozen benchmark membership changed')
    return rows, manifest


def request(utterance, question, key):
    payload = {'state': utterance, 'model': model, 'questions': {'C01': question}}
    req = Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                  headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}, method='POST')
    for attempt in range(4):
        started = time.perf_counter()
        try:
            with urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode('utf-8'))
            answer = body['answers']['C01']
            p = answer['noul']
            if body.get('model') != model or answer.get('type') != 'noul' or isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
                raise RuntimeError('Unexpected Jev model or Noul response')
            return {'probability': p, 'latency_seconds': time.perf_counter()-started, 'response': body}
        except HTTPError as error:
            if error.code not in (429, 529) or attempt == 3:
                raise RuntimeError(f'TypeSafe HTTP {error.code}; body withheld') from None
            time.sleep(min(2**attempt, 8))
        except URLError as error:
            raise RuntimeError(f'TypeSafe transport failure: {type(error.reason).__name__}') from None
    raise RuntimeError('Retries exhausted')


def run():
    rows, manifest = frozen()
    key = os.environ.get('TYPESAFE_API_KEY')
    if not key:
        raise RuntimeError('TYPESAFE_API_KEY absent; no live calls')
    raw = read('jev_responses.json')
    done = {r['example_id'] for r in raw['responses']}
    if len(done) != len(raw['responses']) or not done.issubset(set(manifest['example_ids'])):
        raise RuntimeError('Inconsistent saved responses')
    for row in rows:
        if row['example_id'] in done:
            continue
        item = request(row['utterance'], manifest['api']['question'], key)
        raw['responses'].append({'example_id': row['example_id'], **item})
        raw['status'] = 'complete' if len(raw['responses']) == len(rows) else 'partial'
        write('jev_responses.json', raw)
        progress = read('run_manifest.json')
        progress.update(status=raw['status'], jev_requests_completed=len(raw['responses']), last_call_utc=datetime.now(timezone.utc).isoformat())
        write('run_manifest.json', progress)
        done.add(row['example_id'])
        print(f"{len(done)}/{len(rows)} {row['example_id']}", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-check', action='store_true')
    mode.add_argument('--run', action='store_true')
    args = parser.parse_args()
    try:
        if args.self_check:
            rows, manifest = frozen()
            assert all(r['utterance'] and isinstance(r['utterance'], str) for r in rows)
            assert manifest['api']['question']['type'] == 'noul'
            print(f'Frozen C01 benchmark and Noul request shape verified: {len(rows)} examples')
        else:
            run()
    except RuntimeError as error:
        parser.exit(1, f'{error}\n')
