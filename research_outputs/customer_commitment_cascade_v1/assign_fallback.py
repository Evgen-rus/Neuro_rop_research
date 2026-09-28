"""Expose only frozen utterances routed to blind Luna fallback."""
import json
from pathlib import Path

out = Path(__file__).resolve().parent
read = lambda name: json.loads((out/name).read_text(encoding='utf-8'))
if (out/'fallback_assignment.json').exists():
    raise RuntimeError('Fallback assignment already created')
benchmark = read('benchmark.json')['examples']
raw = read('jev_responses.json')
assert raw['status'] == 'complete' and len(raw['responses']) == len(benchmark)
p = {r['example_id']: r['probability'] for r in raw['responses']}
rows = [{'example_id': r['example_id'], 'utterance': r['utterance']} for r in benchmark
        if r['reference'] in ('YES', 'NO') and .30 < p[r['example_id']] < .70]
(out/'fallback_assignment.json').write_text(json.dumps({'classifier_id': 'C01', 'examples': rows}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'{len(rows)} blind fallback examples')
