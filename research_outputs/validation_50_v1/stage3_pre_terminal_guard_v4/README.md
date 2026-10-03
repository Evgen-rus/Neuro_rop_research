# Preserved inputs before terminal-refusal guard

Historical input freeze and exact builder preserved before correcting a missed explicit terminal refusal in deal6841 (`manager_worklog:2479269:0`, original source_line39). The note said that our option had been declined; its subjectless wording escaped the existing terminal rule. Current research views apply that rule and its suffix cutoff to the missing wording. Baseline files and source retention policy stay intact.

The exposed unfrozen draft is preserved separately in `audit_revisions/6841_pre_terminal_guard.json`; a fresh worker must audit the corrected input. All other input reuse requires byte comparison.
