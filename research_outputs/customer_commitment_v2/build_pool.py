"""Build outcome-blind clean customer utterances from source timelines."""
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location('j01_cleaner', OUT.parent / 'jev_clean_benchmark_v2/build_pool.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
clean = module.clean

unsafe = re.compile(r'(?i)отказались от покупки|отбой по всем проектам|\b[\w.+-]+@[\w.-]+\b|https?://|\+7\s?\(?\d{3}|^сообщение$')
rows, excluded = [], Counter()
seen = set()
for path in sorted((ROOT / 'dataset/deals').glob('*/clean_timeline.jsonl')):
    for line_no, line in enumerate(path.open(encoding='utf-8'), 1):
        event = json.loads(line)
        if event.get('event_type') not in ('message', 'email') or event.get('direction') != 'incoming':
            continue
        value = clean(event.get('content'), event['event_type'])
        if not value or unsafe.search(value):
            excluded['empty_system_pii_or_outcome'] += 1
            continue
        signature = value.casefold()
        if signature in seen:
            excluded['duplicate'] += 1
            continue
        seen.add(signature)
        source = {'deal_id': path.parent.name, 'line': line_no, 'timestamp': event.get('timestamp'),
                  'event_type': event['event_type'], 'source_ids': event.get('metadata', {}).get('source_ids')}
        rows.append({'utterance': value, 'source': source})

for name in ('call_candidates_a.json', 'call_candidates_b.json'):
    for row in json.loads((OUT / name).read_text(encoding='utf-8')):
        value = row['utterance'].strip()
        if not value or unsafe.search(value):
            excluded['call_pii_or_outcome'] += 1
            continue
        signature = value.casefold()
        if signature in seen:
            excluded['duplicate'] += 1
            continue
        seen.add(signature)
        source = {k: row[k] for k in ('deal_id', 'line', 'timestamp', 'event_type', 'activity_id')}
        source['source'] = 'max_voice'
        rows.append({'utterance': value, 'source': source,
                     'attribution_evidence': row['attribution_evidence']})

for row in rows:
    src = row['source']
    key = f"{src['deal_id']}:{src['line']}:{row['utterance']}"
    row['example_id'] = 'C01v2-' + hashlib.sha256(key.encode()).hexdigest()[:12]
assert len({r['example_id'] for r in rows}) == len(rows)
old = json.loads((OUT.parent / 'customer_commitment_cascade_v1/benchmark.json').read_text(encoding='utf-8'))
old_text = {r['utterance'].strip().casefold() for r in old['examples']}
for row in rows:
    row['old_benchmark_overlap'] = row['utterance'].strip().casefold() in old_text
(OUT / 'candidate_pool.json').write_text(json.dumps({'classifier_id': 'C01v2', 'examples': rows}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(OUT / 'labels/label_input.json').write_text(json.dumps({'examples': [{'example_id': r['example_id'], 'utterance': r['utterance']} for r in rows]}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(OUT / 'source_manifest.json').write_text(json.dumps({'source': 'dataset/deals/*/clean_timeline.jsonl', 'outcomes_used': False,
    'sources': dict(Counter(r['source'].get('source', r['source']['event_type']) for r in rows)), 'exclusions': dict(excluded),
    'total': len(rows), 'old_benchmark_overlap': sum(r['old_benchmark_overlap'] for r in rows),
    'call_extraction_files': ['call_candidates_a.json', 'call_candidates_b.json']}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(len(rows), dict(Counter(r['source']['event_type'] for r in rows)), dict(excluded))
