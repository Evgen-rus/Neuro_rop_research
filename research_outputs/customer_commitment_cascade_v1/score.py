"""Score frozen C01 Jev-only and Jev→Luna cascade results."""
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

out = Path(__file__).resolve().parent
read = lambda name: json.loads((out / name).read_text(encoding='utf-8'))
write = lambda name, value: (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
manifest = read('benchmark_manifest.json')
for name, digest in manifest['sha256'].items():
    assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest, name
benchmark = read('benchmark.json')['examples']
raw = read('jev_responses.json')
assert raw['status'] == 'complete' and len(raw['responses']) == len(benchmark)
responses = {r['example_id']: r for r in raw['responses']}
assert len(responses) == len(benchmark) and set(responses) == {r['example_id'] for r in benchmark}
assert all(r['response']['model'] == 'jev-1.13.0' for r in responses.values())
consensus = [r for r in benchmark if r['reference'] in ('YES', 'NO')]
yes_count = sum(r['reference'] == 'YES' for r in consensus)
no_count = len(consensus) - yes_count
assignment = read('fallback_assignment.json')['examples']
fallback_ids = {r['example_id'] for r in assignment}
expected_fallback = {r['example_id'] for r in consensus if .30 < responses[r['example_id']]['probability'] < .70}
assert fallback_ids == expected_fallback
labels = read('luna_fallback_labels.json')
assert set(labels) == fallback_ids and all(v in ('YES', 'NO') for v in labels.values())
rows = []
for example in consensus:
    eid = example['example_id']
    p = responses[eid]['probability']
    jev = 'YES' if p >= .50 else 'NO'
    route = 'JEV' if p >= .70 or p <= .30 else 'LUNA'
    luna = labels[eid] if route == 'LUNA' else None
    final = ('YES' if p >= .70 else 'NO') if route == 'JEV' else luna
    rows.append({'example_id': eid, 'reference': example['reference'], 'jev_probability': p,
                 'route': route, 'jev_prediction': jev, 'luna_prediction': luna,
                 'final_prediction': final, 'correct': final == example['reference']})
write('predictions.json', rows)


def confusion(prediction):
    tp = sum(r['reference'] == 'YES' and r[prediction] == 'YES' for r in rows)
    tn = sum(r['reference'] == 'NO' and r[prediction] == 'NO' for r in rows)
    fp = sum(r['reference'] == 'NO' and r[prediction] == 'YES' for r in rows)
    fn = sum(r['reference'] == 'YES' and r[prediction] == 'NO' for r in rows)
    assert tp+tn+fp+fn == len(rows)
    return {'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn,
            'overall_agreement': (tp+tn)/len(rows), 'YES_agreement': tp/yes_count,
            'NO_agreement': tn/no_count}


jev_metrics = confusion('jev_prediction')
cascade = confusion('final_prediction')
luna_count = sum(r['route'] == 'LUNA' for r in rows)
jev_errors = sum(r['route'] == 'JEV' and not r['correct'] for r in rows)
luna_errors = sum(r['route'] == 'LUNA' and not r['correct'] for r in rows)
cascade.update({'jev_routed': len(rows)-luna_count, 'luna_routed': luna_count,
                'LLM_call_rate': luna_count/len(rows), 'LLM_call_reduction': 1-luna_count/len(rows),
                'jev_auto_routed_errors': jev_errors, 'luna_fallback_errors': luna_errors,
                'original_jev_errors_saved': sum(r['route'] == 'LUNA' and r['jev_prediction'] != r['reference'] and r['correct'] for r in rows),
                'oracle_fallback_ceiling': 1-jev_errors/len(rows)})
assert jev_errors + luna_errors == cascade['FP'] + cascade['FN']
gates = (cascade['overall_agreement'] >= .95 and cascade['YES_agreement'] >= .90 and
         cascade['NO_agreement'] >= .90 and cascade['LLM_call_reduction'] >= .60)
latency = [r['latency_seconds'] for r in responses.values()]
usage = [r['response'].get('usage', {}) for r in responses.values()]
metrics = {'reference_count': len(rows), 'reference_YES': yes_count, 'reference_NO': no_count,
           'disputed_excluded': len(benchmark)-len(rows), 'size_target_met': yes_count >= 50 and no_count >= 50,
           'jev_only_0.50': jev_metrics, 'cascade_0.70_0.30': cascade,
           'acceptance_metric_gates_pass': gates,
           'jev_latency_seconds_median': statistics.median(latency),
           'jev_usage': {'input_tokens': sum(u.get('input_tokens', 0) for u in usage),
                         'output_tokens': sum(u.get('output_tokens', 0) for u in usage),
                         'missing': sum(not u for u in usage)}}
write('metrics.json', metrics)
by_id = {r['example_id']: r for r in consensus}
lines = ['# C01 cascade error analysis', '', f"Final errors: {cascade['FP']+cascade['FN']}. Jev auto-routed: {jev_errors}; Luna fallback: {luna_errors}.", '']
for row in rows:
    if row['correct']:
        continue
    error_source = 'CONFIDENT_JEV_ERROR' if row['route'] == 'JEV' else 'LUNA_FALLBACK_ERROR'
    lines += [f"- `{row['example_id']}`: reference {row['reference']}, Jev p={row['jev_probability']:.2f}, route {row['route']}, final {row['final_prediction']}, {error_source}.",
              f"  Utterance: {by_id[row['example_id']]['utterance']}"]
if all(r['correct'] for r in rows):
    lines.append('No final errors.')
(out/'error_analysis.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
progress = read('run_manifest.json')
progress.update(status='scored', scored_at_utc=datetime.now(timezone.utc).isoformat(),
                reference_count=len(rows), fallback_count=luna_count, acceptance_metric_gates_pass=gates,
                size_target_met=metrics['size_target_met'],
                outputs_sha256={name: hashlib.sha256((out/name).read_bytes()).hexdigest() for name in
                                ('classifier_contract.md', 'preprocessing_rules.md', 'candidate_pool.json',
                                 'labels/label_input.json', 'labels/labeler_A.json', 'labels/labeler_B.json',
                                 'benchmark.json', 'benchmark_manifest.json', 'jev_responses.json',
                                 'fallback_assignment.json', 'luna_fallback_labels.json', 'predictions.json',
                                 'metrics.json', 'error_analysis.md')})
write('run_manifest.json', progress)
print(json.dumps(metrics, ensure_ascii=False, indent=2))
