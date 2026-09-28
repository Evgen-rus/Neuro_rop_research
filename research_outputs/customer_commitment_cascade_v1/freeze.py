"""Freeze C01 consensus benchmark and routing before Jev calls."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

out = Path(__file__).resolve().parent
read = lambda name: json.loads((out / name).read_text(encoding='utf-8'))
write = lambda name, value: (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
sha = lambda name: hashlib.sha256((out / name).read_bytes()).hexdigest()
if (out / 'benchmark_manifest.json').exists():
    raise RuntimeError('C01 benchmark is already frozen')
pool = read('candidate_pool.json')['examples']
ids = [r['example_id'] for r in pool]
labels = []
for name in ('A', 'B'):
    rows = read(f'labels/labeler_{name}.json')
    if [r['example_id'] for r in rows] != ids or any(r['label'] not in ('YES', 'NO') for r in rows):
        raise RuntimeError(f'Invalid independent labeler {name}')
    labels.append({r['example_id']: r['label'] for r in rows})
yes = [r for r in pool if labels[0][r['example_id']] == labels[1][r['example_id']] == 'YES']
no = [r for r in pool if labels[0][r['example_id']] == labels[1][r['example_id']] == 'NO']
disputed = [r for r in pool if labels[0][r['example_id']] != labels[1][r['example_id']]]
hard = re.compile(r'(?i)постара|попробу|надо|нужно|возможно|может|позже|жду|передал|посмотр|подума|вернёмся|согласован|решени|пришл|отправ|ответ|коллег|директор|инженер|закуп')
chosen = []
for hard_first in (True, False):
    groups = defaultdict(list)
    for row in no:
        if bool(hard.search(row['utterance'])) == hard_first:
            groups[row['source']['deal_id']].append(row)
    while groups and len(chosen) < 50:
        for deal in sorted(list(groups)):
            chosen.append(groups[deal].pop(0))
            if not groups[deal]:
                del groups[deal]
            if len(chosen) == 50:
                break
selected = yes + chosen + disputed
selected.sort(key=lambda r: ids.index(r['example_id']))
benchmark = [{'example_id': r['example_id'], 'utterance': r['utterance'],
              'reference': labels[0][r['example_id']] if labels[0][r['example_id']] == labels[1][r['example_id']] else 'DISPUTED'}
             for r in selected]
counts = Counter(r['reference'] for r in benchmark)
write('benchmark.json', {'classifier_id': 'C01', 'examples': benchmark})
question = {
    'type': 'noul',
    'instructions': 'Does this customer utterance explicitly commit the customer or a customer-side person/team to a concrete future action?',
    'criteria': {
        'true': 'YES only when this utterance explicitly asserts that a customer-side owner, including unambiguous first-person or customer-side team, will perform a specific future action. A deadline is optional if the action is clear.',
        'false': 'NO for no explicit concrete future customer-side commitment: generic intention, possibility, tentative effort without commitment, need to discuss, past action, waiting for another decision, interest, or asking the seller to act. Do not infer from surrounding context.'}}
frozen_files = ('classifier_contract.md', 'preprocessing_rules.md', 'candidate_pool.json',
                'labels/label_input.json', 'labels/labeler_A.json', 'labels/labeler_B.json', 'benchmark.json')
write('benchmark_manifest.json', {
    'classifier_id': 'C01', 'example_ids': [r['example_id'] for r in benchmark], 'counts': dict(counts),
    'pool_consensus': {'YES': len(yes), 'NO': len(no), 'DISPUTED': len(disputed)},
    'target': {'YES': 50, 'NO': 50}, 'selection': 'all eligible consensus YES, up to 50 source-diverse consensus NO prioritizing commitment-boundary hard negatives, all disputed',
    'sha256': {name: sha(name) for name in frozen_files},
    'api': {'url': 'https://api.typesafe.ai/v1/systemone', 'model': 'jev-1.13.0', 'question': question},
    'routing': {'YES_at_least': .70, 'NO_at_most': .30, 'otherwise': 'fresh independent Luna Max fallback'},
    'acceptance': {'overall_at_least': .95, 'YES_at_least': .90, 'NO_at_least': .90, 'LLM_call_reduction_at_least': .60},
    'official_docs': ['https://docs.typesafe.ai/api', 'https://docs.typesafe.ai/models']})
write('jev_responses.json', {'status': 'not_run', 'responses': []})
write('run_manifest.json', {'status': 'frozen_before_jev', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
                            'benchmark_sha256': sha('benchmark.json'), 'manifest_sha256': sha('benchmark_manifest.json'),
                            'outcome_used': False, 'dataset_modified': False, 'jev_requests_completed': 0})
print(f"frozen total={len(benchmark)} YES={counts['YES']} NO={counts['NO']} DISPUTED={counts['DISPUTED']} pool_consensus_YES={len(yes)}")
