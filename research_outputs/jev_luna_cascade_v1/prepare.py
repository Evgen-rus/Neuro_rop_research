import json
import hashlib
from pathlib import Path

out = Path(__file__).resolve().parent
src = out.parent / 'jev_clean_benchmark_v2'
load = lambda name: json.loads((src / name).read_text(encoding='utf-8'))
save = lambda name, obj: (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
benchmark = load('clean_benchmark.json')['examples']
raw = load('raw_responses.json')
assert raw['status'] == 'complete' and len(benchmark) == len(raw['responses']) == 98
responses = {r['example_id']: r for r in raw['responses']}
assert len(responses) == 98 and all(r['response']['model'] == 'jev-1.13.0' for r in responses.values())
examples = [e for e in benchmark if e['reference'] in ('YES', 'NO')]
assert len(examples) == 92 and sum(e['reference'] == 'YES' for e in examples) == 42
union = [e for e in examples if .20 < responses[e['example_id']]['probability'] < .80]
assert len(union) == 21
save('cascade_plan.json', {
    'classifier_id': 'J01', 'reference_count': 92, 'yes': 42, 'no': 50, 'disputed_excluded': 6,
    'jev_model': 'jev-1.13.0', 'primary': {'yes_at_least': .70, 'no_at_most': .30},
    'secondary': {'yes_at_least': .80, 'no_at_most': .20},
    'acceptance_primary': {'overall_at_least': .95, 'yes_at_least': .90, 'no_at_least': .90, 'llm_reduction_at_least': .60},
    'source_sha256': {name: hashlib.sha256((src / name).read_bytes()).hexdigest() for name in ('classifier_contract.json', 'clean_benchmark.json', 'raw_responses.json')},
})
save('fallback_assignment.json', {'classifier_id': 'J01', 'examples': [
    {'example_id': e['example_id'], 'utterance': e['utterance']} for e in union]})
print('Prepared 92 consensus examples and 21 blind fallback examples')
