"""Score frozen Jev probabilities with one independent blind Luna fallback run."""

import hashlib
import json
from pathlib import Path

out = Path(__file__).resolve().parent
src = out.parent / 'jev_clean_benchmark_v2'
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
save = lambda name, value: (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
plan = read(out / 'cascade_plan.json')
for name, digest in plan['source_sha256'].items():
    assert hashlib.sha256((src / name).read_bytes()).hexdigest() == digest, name
examples = [e for e in read(src / 'clean_benchmark.json')['examples'] if e['reference'] in ('YES', 'NO')]
responses = {r['example_id']: r for r in read(src / 'raw_responses.json')['responses']}
assignment = read(out / 'fallback_assignment.json')['examples']
labels = read(out / 'luna_labels.json')
assert len(examples) == 92 and len(assignment) == 21
assert set(labels) == {e['example_id'] for e in assignment}
assert all(v in ('YES', 'NO') for v in labels.values())
assert {e['example_id'] for e in assignment} == {e['example_id'] for e in examples if .20 < responses[e['example_id']]['probability'] < .80}
all_predictions = {}
all_metrics = {}
error_lines = ['# Cascade errors', '', 'Each utterance below is a frozen customer utterance. Reference labels remain unchanged.', '']
for threshold, no_threshold in ((.70, .30), (.80, .20)):
    mode = f'{threshold:.2f}/{no_threshold:.2f}'
    rows = []
    for e in examples:
        eid = e['example_id']
        p = responses[eid]['probability']
        route = 'JEV' if p >= threshold or p <= no_threshold else 'LUNA'
        jev_prediction = 'YES' if p >= .50 else 'NO'
        luna_prediction = labels[eid] if route == 'LUNA' else None
        final_prediction = (('YES' if p >= threshold else 'NO') if route == 'JEV' else luna_prediction)
        rows.append({'example_id': eid, 'reference': e['reference'], 'jev_probability': p,
                     'route': route, 'jev_prediction': jev_prediction, 'luna_prediction': luna_prediction,
                     'final_prediction': final_prediction, 'correct': final_prediction == e['reference']})
    all_predictions[mode] = rows
    tp = sum(r['reference'] == 'YES' and r['final_prediction'] == 'YES' for r in rows)
    tn = sum(r['reference'] == 'NO' and r['final_prediction'] == 'NO' for r in rows)
    fp = sum(r['reference'] == 'NO' and r['final_prediction'] == 'YES' for r in rows)
    fn = sum(r['reference'] == 'YES' and r['final_prediction'] == 'NO' for r in rows)
    luna_count = sum(r['route'] == 'LUNA' for r in rows)
    jev_errors = sum(r['route'] == 'JEV' and not r['correct'] for r in rows)
    luna_errors = sum(r['route'] == 'LUNA' and not r['correct'] for r in rows)
    saved = sum(r['route'] == 'LUNA' and r['jev_prediction'] != r['reference'] and r['correct'] for r in rows)
    assert tp + tn + fp + fn == 92 and jev_errors + luna_errors == fp + fn
    overall, yes, no, reduction = (tp+tn)/92, tp/42, tn/50, 1-luna_count/92
    all_metrics[mode] = {
        'final_overall_agreement': overall, 'final_yes_agreement': yes, 'final_no_agreement': no,
        'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn, 'jev_routed_count': 92-luna_count,
        'luna_routed_count': luna_count, 'llm_call_rate': luna_count/92, 'llm_call_reduction': reduction,
        'jev_auto_routed_errors': jev_errors, 'luna_fallback_errors': luna_errors,
        'original_jev_errors_saved_by_fallback': saved, 'oracle_fallback_ceiling': 1-jev_errors/92,
        'llm_calls_avoided': 92-luna_count, 'jev_calls': 92,
        'acceptance_pass': overall >= .95 and yes >= .90 and no >= .90 and reduction >= .60}
    error_lines += [f'## {mode}', '']
    for r in rows:
        if r['correct']:
            continue
        source = 'CONFIDENT_JEV_ERROR' if r['route'] == 'JEV' else 'LUNA_FALLBACK_ERROR'
        utterance = next(e['utterance'] for e in examples if e['example_id'] == r['example_id'])
        error_lines += [f"- `{r['example_id']}`: reference {r['reference']}; Jev p={r['jev_probability']:.2f}; route {r['route']}; final {r['final_prediction']}; {source}.",
                        f'  Utterance: {utterance}']
    if not any(not r['correct'] for r in rows):
        error_lines.append('No final errors.')
    error_lines.append('')
save('predictions.json', all_predictions)
save('metrics.json', {'reference_count': 92, 'reference_yes': 42, 'reference_no': 50,
                      'jev_only_0.50_agreement': 78/92, 'jev_median_latency_seconds': read(src/'metrics.json')['latency_seconds']['median'],
                      'fallback_luna_latency_seconds': None, 'cascade': all_metrics})
(out/'error_analysis.md').write_text('\n'.join(error_lines), encoding='utf-8')
print(json.dumps(all_metrics, ensure_ascii=False, indent=2))
