"""Reuse the audited outcome-blind J01 customer utterance extraction for C01."""
import hashlib
import json
import re
from pathlib import Path

out = Path(__file__).resolve().parent
source = out.parent / 'jev_clean_benchmark_v2' / 'candidate_pool.json'
prior = json.loads(source.read_text(encoding='utf-8'))['examples']
excluded_ids = {'J01-f8ada0f740c4', 'J01-0c9f33a1083d', 'J01-8ea4f72d9572', 'J01-45bbcd29b323', 'J01-a87ec6c9b044'}
unsafe = re.compile(r'(?i)отказались от покупки|отбой по всем проектам|\b[\w.+-]+@[\w.-]+\b|https?://|\+7\s?\(?\d{3}|^сообщение$')
rows, exclusions = [], {}
for row in prior:
    reason = ('audited_quoted_text' if row['example_id'] in excluded_ids else
              'uncertain_source' if row['source']['deal_id'] == '5971' else
              'pii_or_outcome_text' if unsafe.search(row['utterance']) else None)
    if reason:
        exclusions[reason] = exclusions.get(reason, 0) + 1
        continue
    source_key = f"{row['source']['deal_id']}:{row['source']['line']}"
    rows.append({'example_id': 'C01-' + hashlib.sha256(source_key.encode()).hexdigest()[:12],
                 'utterance': row['utterance'], 'source': row['source']})
assert len({r['example_id'] for r in rows}) == len(rows)
assert all(r['utterance'] for r in rows)
out.joinpath('candidate_pool.json').write_text(json.dumps({
    'classifier_id': 'C01', 'source': str(source.relative_to(out.parent)),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'exclusions': exclusions, 'examples': rows}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
out.joinpath('labels', 'label_input.json').write_text(json.dumps({
    'classifier_id': 'C01', 'examples': [{'example_id': r['example_id'], 'utterance': r['utterance']} for r in rows]},
    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(rows)} candidates; exclusions={exclusions}')
