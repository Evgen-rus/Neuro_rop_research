import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

out = Path(__file__).resolve().parent
files = ('cascade_plan.json', 'fallback_assignment.json', 'luna_labels.json', 'predictions.json', 'metrics.json', 'error_analysis.md', 'executive_summary.md')
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest = {
    'benchmark': 'Jev → Luna Cascade Benchmark v1', 'status': 'complete',
    'completed_at_utc': datetime.now(timezone.utc).isoformat(),
    'source': 'research_outputs/jev_clean_benchmark_v2', 'classifier': 'J01',
    'reference_examples': 92, 'disputed_excluded': 6, 'luna_union_examples': 21,
    'luna_worker': 'fresh independent Luna Max worker; blind to Jev and reference',
    'new_jev_calls': 0, 'outcome_used': False, 'dataset_modified': False,
    'files_sha256': {name: digest(out / name) for name in files},
}
(out / 'run_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
