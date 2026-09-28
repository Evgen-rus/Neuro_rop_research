# C01 cascade error analysis

Final errors: 2. Jev auto-routed: 1; Luna fallback: 1.

- `C01-cd373220454e`: reference NO, Jev p=0.58, route LUNA, final YES, LUNA_FALLBACK_ERROR.
  Utterance: Александр, у нас завтра встреча с коллегами
- `C01-4c399bca0b6c`: reference YES, Jev p=0.17, route JEV, final NO, CONFIDENT_JEV_ERROR.
  Utterance: Нет, остановимся на вакууме

Both final errors sit near the C01 semantic boundary. “У нас завтра встреча с коллегами” names a future customer-side meeting but the frozen consensus labeled it NO, apparently treating a schedule statement as distinct from an explicit promise. “Остановимся на вакууме” was frozen as YES by both reference labelers, though it may be read as a choice rather than a separate future customer action. The blind fallback worker also noted that “Планируем установить” was borderline and labeled it YES. These observations are error analysis only; no contract, reference, routing, or score was changed after Jev results.
