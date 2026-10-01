Продолжаем исследование в:

`D:\My_dev_project\Neuro_rop_research`

Основной operational source:

`D:\My_dev_project\Neuro_rop_practice`

Ты - основной оркестратор исследования. Используй существующие правила агентов и субагентов из репозитория. Сам распределяй независимые задачи между доступными workers, когда это действительно ускоряет работу.

## Execution plan — validation 50, 2026-10-01

Stage 1 завершён, cohort frozen: 50 новых сделок, 25 WON / 25 LOST,
baseline overlap 0. Артефакты: `research_outputs/validation_50_v1/cohort.json`
и `closed_deal_pool.json`. Пахомов: 27/50; 10 менеджеров; pipelines
15:32, 17:10, 47:8; период 2026-01-16 — 2026-09-30.
Баланс 25/25 задан sampling design и не является conversion rate компании.

Stage 2–6 выполняются последовательно без отдельного разрешения на каждый этап.
CHECKPOINT теперь означает внутренний validation gate. Переход к следующему
этапу выполняется автоматически только после PASS предыдущего gate.

Последовательность: completeness штатным pipeline → отдельный validation dataset
→ 50 основных blind audits по schema v2 → 12–15 независимых selective reliability
audits → canonical freeze и проверка hashes → reveal outcomes → T1–T5,
open discovery, manager robustness → business findings и executive summary.
Reliability sample выбирается outcome-blind; два полных прохода по 50 не нужны.

Hard gate Stage 2: `eligible_calls_without_transcript = 0` для measured audio >=36 sec.
Dataset gate: точные frozen 50 IDs, baseline overlap 0, отдельные labels,
completeness PASS, deterministic integrity. Freeze primary и canonical audits
до reveal. Reliability не должна быть явно хуже baseline 23.

Остановка только после Stage 6 либо при настоящем blocker: невыполнимый hard gate,
существенная неполнота/повреждение данных, необходимость изменить методологию v2,
записи в Bitrix/существенного production change или неоднозначность,
способная существенно изменить выводы. Обычные технические проблемы решать
штатными средствами самостоятельно.

Старые datasets и deal_audit_v1/v2 неизменяемы. Новые артефакты только в
`research_outputs/validation_50_v1/`. Bitrix read-only; существующий pipeline
истории/audio/transcription разрешён для точных 50 IDs. Нет production integration,
Jev, classifiers, predictive ML или расширения cohort. После финала commit и push.
---

# Цель

Проверить уже разработанную методику retrospective deal audit на новой выборке примерно из **50 закрытых сделок**.

Нужно понять:

- сохраняются ли найденные на первых 23 сделках паттерны;
- какие исчезают;
- какие усиливаются;
- какие новые повторяющиеся паттерны появляются;
- какие из них реально управляемы менеджером или компанией;
- что потенциально стоит потом встроить в живой `Neuro_rop_practice`.

Это валидационный этап.

Не надо снова уходить в исследования Jev, atomic classifiers или predictive ML.
---

# Существующий baseline

Не изменять и не удалять:

- `dataset/`
- `dataset_v2/`, если существует под таким именем
- `research_outputs/deal_audit_v1/`
- `research_outputs/deal_audit_v2/`

`deal_audit_v2` - текущий validated baseline.

Известные candidate patterns T1-T5 использовать как **гипотезы для проверки**, а не как заранее истинные категории.

Новая выборка может их подтвердить, ослабить, изменить или выявить новые паттерны.
---

# INTERNAL GATE 1 — cohort (historical; completed)

Stage 1 завершён и заморожен: `research_outputs/validation_50_v1/cohort.json`
и `closed_deal_pool.json`. Повторный sampling не выполняется.
---

# INTERNAL GATE 2 — completeness и подготовка источников

Для утверждённых 50 сделок использовать **существующий pipeline `Neuro_rop_practice`**.

Не писать отдельный downloader/transcriber.

Проверить для каждой сделки:

- CRM history;
- calls;
- emails/messages;
- relevant comments/tasks;
- audio manifests;
- transcripts.

Использовать действующее правило звонков:

`measured audio >= 36 sec → должен иметь transcript`

Для всех доступных eligible calls:
- найти существующий transcript;
- если его нет и audio доступно - транскрибировать штатным pipeline;
- Bitrix только read-only.

Отдельно учитывать:
- calls без доступного audio;
- unknown duration;
- missing CRM data.

Не считать отсутствие данных отрицательным свидетельством.

## Hard gate

Перед дальнейшим analysis:

```text
eligible_calls_without_transcript == 0
```

Если gate не пройден - остановиться.


Ответить:

```text
Сделок проверено: 50

Всего звонков: X
Eligible >=36 sec: X
С transcript: X
Восстановлено сейчас: X
Eligible без transcript: X

Audio unavailable / unknown duration: X

Сделки с серьёзным data-quality risk:
...

DATA READY: YES / NO
```
---

# INTERNAL GATE 3 — собрать новый validation dataset

Создать отдельный versioned dataset для cohort 50.

Не изменять старые datasets.

Структуру и semantic contract максимально сохранить совместимыми с v2:

- `manifest`
- `summary`
- `build_quality`
- `deals/<id>/neutral.json`
- `deals/<id>/clean_timeline.jsonl`

Использовать lessons learned v2:
- source provenance;
- activity_id linkage;
- chronology;
- direct customer evidence отдельно от manager worklog;
- data-quality metadata;
- outcome leakage protection.

Проверить deterministic integrity и completeness.



Ответить:

```text
Dataset: READY / NOT READY

Deals: 50

WON/LOST:
...

Data-quality hard gate: PASS / FAIL

Размер:
events ...
примерный text volume ...

Основные ограничения:
...
```
---

# INTERNAL GATE 4 — основной blind audit 50 сделок

Это основной semantic pass.

Каждая сделка анализируется **один раз** outcome-blind.

Не делать автоматически два полных анализа каждой сделки.

Использовать frozen schema и методику `deal_audit_v2`, если нет объективной причины изменить её.

Workers не должны видеть:
- WON/LOST;
- итоговые T1-T5 memberships;
- portfolio findings;
- audits других сделок.

По сделке определить:

- trajectory;
- customer need/state;
- turning points;
- positive/negative signals;
- manager strong actions;
- possible manager/process gaps;
- controllability;
- uncertainties;
- evidence pointers.

Не заставлять модель обязательно находить ошибку менеджера.

`no clear controllable issue` - допустимый результат.

Сохранить frozen results перед reveal outcomes.


Ответить:

```text
Blind audits complete: X/50

Failed / insufficient evidence: X

High data-quality concern: X

Без раскрытия WON/LOST:
- общие типы наблюдаемых ситуаций;
- где audits чаще всего неуверенны;
- есть ли проблемы schema/prompt.

AUDIT PASS READY FOR VALIDATION: YES / NO
```
---

# INTERNAL GATE 5 — selective reliability check

Не повторять все 50.

Выбрать примерно **12–15 сделок** для второго независимого blind audit.

Sampling должен включать:

- часть случайных сделок;
- самые неуверенные audits;
- несколько сделок с потенциально сильным manager/process conclusion;
- разные managers; sample выбирается строго outcome-blind без использования WON/LOST для отбора.

Второй worker не видит первый audit.

Сравнить semantic agreement:

- primary explanation;
- controllability;
- turning point;
- manager/process opportunity;
- strongest customer signals.

Категории:

`AGREE / PARTIAL / DISAGREE`

При DISAGREE проверить source evidence.


Ответить:

```text
Double-audited: X

Primary explanation:
AGREE X
PARTIAL X
DISAGREE X

Controllability:
...

Manager/process opportunity:
...

Главные причины disagreement:
...

METHOD STABLE ENOUGH: YES / NO
```
---

# INTERNAL GATE 6 — reveal outcomes и portfolio analysis

Только теперь присоединить WON/LOST.

Сначала проверить старые hypotheses T1-T5 на новом cohort.

Для каждого:

- LOST count / denominator;
- WON count / denominator;
- counterexamples;
- managers involved;
- data-quality caveats.

Не ограничиваться T1-T5.

Отдельно сделать open discovery повторяющихся новых patterns.

Новый pattern разрешено считать существенным candidate только если:
- он повторяется в нескольких независимых сделках;
- evidence не основано только на manager worklogs;
- это не просто другое название существующего T1-T5.

Разделять:

- manager-controllable;
- company/process-controllable;
- partially controllable;
- customer/external;
- unknown.

Не утверждать causality.

Не делать predictive model.


Остановиться и дать бизнес-результат.

Формат:

```text
Исследовано: 50 новых сделок

T1: ...
T2: ...
T3: ...
T4: ...
T5: ...

Подтвердились:
...

Ослабли/исчезли:
...

Новые повторяющиеся patterns:
...

Самые интересные управляемые точки:
1. ...
2. ...
3. ...

Что пока нельзя утверждать:
...

Рекомендация следующего шага:
...
```
---

# Общие ограничения

Не делать без отдельной команды:

- Jev experiments;
- atomic classifier research;
- predictive ML;
- production integration;
- изменение live NeuroROP recommendations;
- автоматические изменения Bitrix;
- расширение сразу до сотен/тысяч сделок.

Не раздувать инфраструктуру ради исследования.

Использовать существующий код и manifests, где это возможно.

При настоящем blocker остановить исследование и описать конкретную причину
и минимальный вариант решения. Не запускать последующие этапы через failed gate.

Главное: **получить надёжный ответ с минимальным количеством лишней работы и LLM-прогонов.**
