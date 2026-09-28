# J01 error analysis

At threshold 0.50: 14 false negatives, 0 false positives. All 14 had consensus YES from both independent labelers. The labels and frozen benchmark were not revised after Jev responses.

| Example | Reference | Jev p(YES) | Error type | Customer utterance |
|---|---|---:|---|---|
| J01-2add08ba2f4f | YES | 0.32 | MISSED_CONSTRAINT | Т. К нам нужно qr код наносить, и приобретать оборудование |
| J01-e10fcd1a76b1 | YES | 0.30 | AMBIGUOUS_REFERENCE | Александр, в вязкости давайте тоже диапазон поставим |
| J01-517c1bc2ee07 | YES | 0.45 | MISSED_CONSTRAINT | + vras@ / Александр спасибо за оперативность! / Мы ещё обсуждали возможность нанесения на этикетку марки честный знак (Дата Матрикс). |
| J01-ffa237058e27 | YES | 0.32 | MISSED_TECH_QUESTION | Это ИИ визуализация или есть конкретный прототип? Можем попробовать на нашей банке и этикетке ? |
| J01-77e7f8b8514e | YES | 0.47 | AMBIGUOUS_REFERENCE | цилиндрическая |
| J01-4c399bca0b6c | YES | 0.41 | MISSED_CONSTRAINT | Нет, остановимся на вакууме |
| J01-f2ae6faa73a2 | YES | 0.40 | MISSED_CONSTRAINT | Давайте без принимающего |
| J01-6cb2066cdb26 | YES | 0.31 | MISSED_CONSTRAINT | Подающий + удлинение |
| J01-3b4881ed9f6e | YES | 0.18 | MISSED_CONSTRAINT | И аппликатор с зеркальной стороны как он в цеху у вас стоял |
| J01-c989de9fca33 | YES | 0.49 | MISSED_TECH_QUESTION | Я так понял в вопросе про крышку имеется ввиду используется ли крышка во время этикирования |
| J01-2d771fa03a9d | YES | 0.46 | AMBIGUOUS_REFERENCE | цилиндрические |
| J01-01ce80962442 | YES | 0.10 | AMBIGUOUS_REFERENCE | разные овальные сложные |
| J01-f6eb5b7f5f7c | YES | 0.39 | AMBIGUOUS_REFERENCE | Бушон, Цилиндрические, Ромб,Биокон оранжевый, и любую другую сложную форму |
| J01-0c8f489bb3fa | YES | 0.46 | AMBIGUOUS_REFERENCE | Добрый день Александр! К разговору про комплекс оборудования для ЧЗ, который мы у вас брали. Ждем от вас КП на всё тоже самое, кроме прижимного устройства. |

Type concentration: 6 AMBIGUOUS_REFERENCE, 6 MISSED_CONSTRAINT, 2 MISSED_TECH_QUESTION. No MISSED_PARAMETER or GENERIC_TECH_CONTEXT_FALSE_POSITIVE at the main threshold.

Six false negatives are short, elliptical, or depend on unstated referents. They raise a gold-boundary concern even though both labelers agreed: a one-utterance classifier may reasonably read them as lacking a self-contained requirement. The other eight include explicit technical choices or answerable questions, so the low YES recall cannot be attributed only to these ambiguous references. This is an interpretive audit, not post-hoc relabeling.

The 6 Luna-disputed examples were called but excluded from the score:

| Example | Jev p(YES) | Customer utterance |
|---|---:|---|
| J01-49c2ad5d7adf | 0.16 | Еще в договоре нет схемы планировки с габаритами, мне ее нужно, можно к договору не лепить, просто мне вышлите письмом с подписью |
| J01-cc30a50f22e5 | 0.17 | По узлам просит чтобы были похожие чертежи |
| J01-f60d6be545b5 | 0.28 | Т. Ев описании каждой позиции дополнить чертежами и деталировкой |
| J01-65ef7f07a293 | 0.12 | Александр, до понедельника пока есть время , я бы предложил каждый блок расширить чертежами |
| J01-d23fa39a2338 | 0.18 | Слицевой стороны |
| J01-5c714a97c6ce | 0.11 | бушон |

At higher predeclared thresholds, errors decrease through abstention: 0.70 has 3 false negatives and 16 abstentions; 0.80 has 2 and 22; 0.90 has 0 and 41. These are not full-coverage outcomes.
