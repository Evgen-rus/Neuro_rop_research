"""Freeze C01v2 reference and record the pre-Jev size gate."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

out = Path(__file__).resolve().parent
read = lambda name: json.loads((out / name).read_text(encoding='utf-8'))
write = lambda name, obj: (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
digest = lambda name: hashlib.sha256((out / name).read_bytes()).hexdigest()
rows = read('candidate_pool.json')['examples']
a, b = read('labels/labeler_A.json'), read('labels/labeler_B.json')
ids = {r['example_id'] for r in rows}
assert len(ids) == len(rows) and set(a) == set(b) == ids
assert set(a.values()) <= {'YES', 'NO'} and set(b.values()) <= {'YES', 'NO'}
benchmark = []
for row in rows:
    eid = row['example_id']
    benchmark.append({**row, 'reference': a[eid] if a[eid] == b[eid] else 'DISPUTED_REFERENCE'})
write('benchmark.json', {'classifier_id': 'C01v2', 'examples': benchmark})
fresh = [r for r in benchmark if not r['old_benchmark_overlap']]
count = lambda group: dict(Counter(r['reference'] for r in group))
all_counts, fresh_counts = count(benchmark), count(fresh)
size_met = fresh_counts.get('YES', 0) >= 50 and fresh_counts.get('NO', 0) >= 50
assert not size_met, 'Size gate passed: run the frozen Jev/cascade phase instead of stopping'
frozen = ('classifier_contract.md', 'source_manifest.json', 'candidate_pool.json',
          'labels/label_input.json', 'labels/labeler_A.json', 'labels/labeler_B.json', 'benchmark.json')
write('benchmark_manifest.json', {'classifier_id': 'C01v2', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
    'example_ids': [r['example_id'] for r in benchmark], 'sha256': {name: digest(name) for name in frozen},
    'reference_counts': {'fresh_only': fresh_counts, 'all': all_counts},
    'old_benchmark_overlap_count': len(benchmark)-len(fresh),
    'pre_jev_size_gate_met': False, 'routing_if_gate_passed': {'jev_only_threshold': 0.50,
    'cascade_yes_at_least': 0.70, 'cascade_no_at_most': 0.30, 'otherwise': 'fresh Luna Max fallback'}})
write('jev_responses.json', {'status': 'not_run_size_gate', 'responses': []})
write('luna_fallback_labels.json', {'status': 'not_run_size_gate', 'labels': {}})
write('metrics.json', {'reference_counts': {'fresh_only': fresh_counts, 'all': all_counts},
    'fresh_only_minimum': {'YES': 50, 'NO': 50}, 'fresh_only_size_gate_met': False,
    'jev_only': None, 'cascade': None, 'acceptance': 'NOT_CONFIRMED_INSUFFICIENT_FRESH_YES'})
(out/'error_analysis.md').write_text('# C01v2 error analysis\n\nJev and cascade were not run: the fresh-only size gate failed. No model errors can be assessed.\n\nThe contract explicitly separates choice from action and scheduled event from commitment; these boundaries remain untested by Jev in v2.\n', encoding='utf-8')
(out/'executive_summary.md').write_text(
    f"# Customer Commitment Benchmark v2\n\n**Verdict: not confirmed.** Fresh-only reference has {fresh_counts.get('YES',0)} consensus YES, {fresh_counts.get('NO',0)} consensus NO, and {fresh_counts.get('DISPUTED_REFERENCE',0)} disputed. Required: at least 50 YES and 50 NO.\n\n"
    f"All extracted examples: {all_counts.get('YES',0)} consensus YES, {all_counts.get('NO',0)} consensus NO, and {all_counts.get('DISPUTED_REFERENCE',0)} disputed; {len(benchmark)-len(fresh)} overlap the old benchmark.\n\n"
    "The 209-candidate pool covered all clean incoming text plus reliably attributed single-speaker voice messages. Undiarized calls could not yield reliable isolated customer turns. No synthetic examples, outcomes, Jev calls, fallback, or predictive analysis were used.\n", encoding='utf-8')
write('run_manifest.json', {'status': 'stopped_before_jev_insufficient_fresh_yes',
    'completed_at_utc': datetime.now(timezone.utc).isoformat(), 'frozen_sha256': digest('benchmark_manifest.json'),
    'output_sha256': {name: digest(name) for name in ('benchmark.json', 'metrics.json', 'error_analysis.md', 'executive_summary.md')}})
print('frozen', fresh_counts, all_counts, 'size gate: STOP')
