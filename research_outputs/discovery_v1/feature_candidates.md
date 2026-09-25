# Каталог кандидатов — discovery_v1

Это гипотезы по наблюдаемым до исхода событиям, не оценка прогностической силы. Широта доказательств — число уникальных сделок, упомянутых в отчётах workers, а не результаты разметки всех 23 сделок.

| ID | Признак | Направление | Jev | Опора WON/LOST/группы | Главный конфаунд | Вердикт критика | Приоритет проверки |
|---|---|---|---|---|---|---|---|
| R01 | Ясность внутреннего решения | чаще в WON (предварительно) | ordinal | 7/5/3 | Manager worklogs summarize the customer process and may overstate certainty. | merge | high |
| R02 | Состояние шага, принадлежащего клиенту | смешанное | choice | 7/7/3 | Different action difficulty: a sample shipment or multi-department review takes longer than a simple call. | merge | high |
| R03 | Достаточность исходных данных клиента | смешанное | ordinal | 7/7/3 | Product complexity and number of formats determine how much data is needed. | merge | medium |
| R04 | Предметность технического запроса | смешанное | ordinal | 7/6/3 | Question frequency can reflect configuration complexity, not buying intent. | merge | medium |
| R05 | Статус проверки технической применимости | смешанное | choice | 5/4/3 | Only two WON cases in this shard have a recorded in-person validation. | merge | medium |
| R06 | Согласие клиента с конкретной конфигурацией | чаще в WON (предварительно) | boolean | 3/3/1 | Product range and project complexity drive scope breadth. | revise | low |
| R07 | Самостоятельное содержательное обращение клиента | смешанное | boolean | 6/4/3 | Visibility depends on the completeness of message/call capture. | merge | medium |
| R08 | Сравнение альтернатив по явному критерию | смешанное | boolean | 3/4/2 | Price gap | merge | low |
| R09 | Формальный шаг закупки со стороны клиента | чаще в WON (предварительно) | ordinal | 5/3/2 | This is late-stage and strongly correlated with deal progression; it may be a status marker rather than an early semantic feature. | merge | low |
| R10 | Явное текущее предпочтение клиента | чаще в WON (предварительно) | choice | 2/1/1 | Seller worklogs may overstate customer preference. | revise | low |

## Границы интерпретации

В каталоге сохранены десять различимых вопросов после объединения 29 исходных формулировок. Согласие с ценой отклонено как самостоятельный признак. R09 относится только к поздней стадии и требует отдельного времени снимка. Для каждого кандидата точные ссылки на события, противопримеры, ограничения и варианты ответа находятся в JSON.

Значения `more_in_won` отражают наблюдения отдельных групп, не подсчитанную частоту во всём датасете. Отсутствие события в таймлайне не доказывает его отсутствие в реальном общении.
