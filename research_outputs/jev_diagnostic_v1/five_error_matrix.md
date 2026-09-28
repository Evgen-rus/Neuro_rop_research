# Five baseline errors across variants

A/B/C use p≥0.50 for YES; D uses its returned Choice. Reference labels were withheld from API requests.

| Example | Reference | A | B | C | D | Interpretation |
|---|---|---|---|---|---|---|
| E06-075 | YES | NO (0.18) | NO (0.08) | NO (0.20) | NO (A=0.08) | NONE |
| E06-078 | YES | NO (0.26) | NO (0.15) | NO (0.26) | NO (A=0.16) | NONE |
| E06-179 | NO | YES (0.69) | YES (0.61) | YES (0.72) | YES (A=0.72) | NONE |
| E06-192 | NO | YES (0.58) | YES (0.59) | YES (0.50) | YES (A=0.64) | NONE |
| E06-193 | NO | YES (0.51) | YES (0.73) | NO (0.33) | YES (A=0.58) | SPEAKER_ATTRIBUTION |

Interpretation labels describe a single paired run; they do not prove causality, especially with N=41 and correlated examples.
