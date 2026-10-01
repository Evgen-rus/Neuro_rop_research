Продолжаем исследование в:

`D:\My_dev_project\Neuro_rop_research`

Основной operational source:

`D:\My_dev_project\Neuro_rop_practice`

Ты - основной оркестратор исследования. Используй существующие правила агентов и субагентов из репозитория. Сам распределяй независимые задачи между доступными workers, когда это действительно ускоряет работу.

Главный принцип: **не делать всё исследование одним большим непрерывным прогоном**.

Работаем по этапам. После каждого CHECKPOINT:
1. остановиться;
2. дать мне короткий отчёт;
3. ничего из следующего этапа не запускать до моей команды.

Я буду передавать этот отчёт внешнему reviewer/РОПу и возвращаться с решением.

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

# STAGE 1 — выбрать cohort из 50 сделок

Сначала НИЧЕГО не транскрибировать и не запускать semantic audits.

Используя штатные read-only возможности `Neuro_rop_practice`, определить доступный пул закрытых сделок.

Предпочтительно выбрать **50 новых сделок, не входящих в исходные 23**.

Если 50 новых качественных сделок получить нельзя - не подменять молча. Показать доступный вариант.

Критерии:

- несколько менеджеров, если данные доступны;
- WON и LOST максимально сбалансированы;
- несколько pipeline допустимы;
- не выбирать сделки только потому, что у них богатая история;
- не cherry-pick по предполагаемым причинам исхода;
- желательно разумно распределить по времени;
- исключить явно технические/пустые сделки, где практически нет бизнес-взаимодействия.

Для предлагаемого cohort показать:

- количество;
- WON / LOST;
- managers;
- pipelines;
- период;
- overlap с исходными 23;
- сколько сделок имеют звонки;
- приблизительную полноту доступных данных.

Если выбор outcome используется для балансировки cohort - это нормально на этапе sampling. Но semantic audit позже должен быть outcome-blind.

## CHECKPOINT 1

Остановиться.

Ответить кратко:

```text
Доступный pool: X

Предлагаемый cohort: 50
WON: X
LOST: X

Менеджеры:
...

Pipeline:
...

Период:
...

Overlap с исходными 23: X

Проблемы/риски выборки:
...

Рекомендация: PROCEED / CHANGE COHORT
```

Не переходить к STAGE 2.

---

# STAGE 2 — completeness и подготовка источников

После отдельного разрешения.

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

## CHECKPOINT 2

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

Не строить research dataset и не запускать Luna deal audits.

---

# STAGE 3 — собрать новый validation dataset

После разрешения.

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

Не начинать semantic analysis.

## CHECKPOINT 3

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

И остановиться.

---

# STAGE 4 — основной blind audit 50 сделок

После разрешения.

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

## CHECKPOINT 4

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

Не раскрывать outcomes и не агрегировать WON/LOST.

---

# STAGE 5 — selective reliability check

После разрешения.

Не повторять все 50.

Выбрать примерно **10-15 сделок** для второго независимого blind audit.

Sampling должен включать:

- часть случайных сделок;
- самые неуверенные audits;
- несколько сделок с потенциально сильным manager/process conclusion;
- разные managers/outcomes, но outcome не показывать worker.

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

## CHECKPOINT 5

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

И остановиться.

---

# STAGE 6 — reveal outcomes и portfolio analysis

После разрешения.

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

## CHECKPOINT 6

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

Если возникает технический затык:
1. сначала разобраться в существующей реализации;
2. не строить параллельный pipeline без необходимости;
3. если решение существенно меняет методику - остановиться на CHECKPOINT и описать проблему.

Главное: **получить надёжный ответ с минимальным количеством лишней работы и LLM-прогонов.**