"""Write the Validation 2A reports from blind labels only."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
KINDS = ("D3", "D7", "T25", "T50", "T80")
DECISIONS = {
    "R01": ("REVISE", "Граница между названным барьером и действующим шагом", "ordinal", "Нет; брать текущий gate", "Нет", "Имя роли, её действие и срок/результат из одной актуальной реплики"),
    "R02": ("SPLIT_SEMANTIC_AND_CODE", "Статус последнего обещания требует истории и расчёта срока", "choice", "Да: последнее клиентское обязательство и его версии", "Да: срок, факт выполнения и число просрочек", "Обещание, ответственный, контрольная дата, подтверждение выполнения и последующие переносы"),
    "R03": ("REVISE", "Нет общего порога достаточности материалов для конкретной задачи", "ordinal", "Текущая версия задачи", "Нет", "Заявленное применение, запрошенные и фактически полученные данные"),
    "R04": ("REVISE", "Разметчики расходятся между UNKNOWN и отсутствием предметного запроса", "ordinal", "Нет", "Нет", "Слова клиента об ограничении или вопросе и связь с проверяемым действием"),
    "R05": ("REVISE", "Размыта граница нерешённого вопроса и обоснованной применимости", "choice", "Да: текущий scope и последняя проверка", "Нет", "Конкретная задача, техническое заключение или результат релевантного теста"),
    "R06": ("REVISE", "Согласие клиента путают с подготовленной продавцом конфигурацией", "boolean", "Да: актуальная конфигурация", "Нет", "Явное подтверждение клиента и версия состава решения"),
    "R07": ("SPLIT_SEMANTIC_AND_CODE", "Инициатор и содержательность смешаны; ответы расходятся", "boolean", "Нет", "Да: направление/инициатор события, если канал надёжен", "Инициированное клиентом событие и его покупательский смысл"),
    "R08": ("REVISE", "Неодинаково трактуются реальная альтернатива и явный критерий", "boolean", "Нет", "Нет", "Названная клиентом альтернатива и критерий из доступного сообщения"),
    "R09": ("REVISE", "Формальный шаг слишком близок к концу и путается с планом продавца", "ordinal", "Да: стадия формального процесса", "Часть статусов документов может извлекаться структурно", "Подтверждённое действие закупок, юристов или финансирования со стороны клиента"),
    "R10": ("REVISE", "Молчание и отсутствие предпочтения смешаны; критерий не всегда явный", "choice", "Да: последнее явное предпочтение", "Нет", "Слова клиента о текущем выборе и названном критерии"),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    agreement = read(HERE / "reliability" / "agreement.json")
    temporal = read(HERE / "temporal_data.json")
    contract = read(HERE / "labeling_contract.json")
    manifest = read(HERE / "snapshot_manifest.json")
    labels = {(str(d["deal_id"]), s["snapshot"], l["feature_id"]): l
              for worker in "ABC" for d in read(HERE / "labels" / f"{worker}.json")["deals"]
              for s in d["snapshots"] for l in s["labels"]}
    assert len(labels) == 1150
    metrics = agreement["metrics"]
    report = {"run_version": "validation_2a", "scope": "blind snapshot labelability and chronology only",
              "denominator_deals": 23, "reliability_sample_snapshots": 23,
              "known_definition": "value != UNKNOWN; negative or absence states may have no positive event citation",
              "evidence_backed_known_definition": "value != UNKNOWN and at least one cited snapshot event",
              "agreement_definitions": {"exact": "same contract value / 23",
                                        "unknown": "both labelers agree whether value is UNKNOWN / 23",
                                        "major": "different values, both non-UNKNOWN / 23"}, "features": []}
    table = ["# Пригодность признаков к слепой разметке — Validation 2A", "",
             "В ячейке `известно/23 (с событием)` первая цифра означает ответ, отличный от `UNKNOWN`; число в скобках — сколько таких ответов имеют ссылку на событие. Отрицательные ответы без события могут отражать недостаток данных, поэтому раннюю наблюдаемость следует читать по обоим числам.", "",
             "| Feature | D3 | D7 | T25 | T50 | T80 | Agreement | Ambiguity | Verdict |",
             "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    jev = ["# Замечания по Jev — Validation 2A", "",
           "Jev рассматривается только как атомарный семантический датчик по `Docs/jev_context.md`. Каталог R01–R10 во время разметки не менялся. Ниже — предложения перед отдельным следующим этапом, не интеграция.", ""]
    for f in contract["features"]:
        fid = f["feature_id"]
        verdict, ambiguity, typ, history, code, minimum = DECISIONS[fid]
        counts = {}
        for kind in KINDS:
            rows = [l for (deal, snap, feature), l in labels.items() if snap == kind and feature == fid]
            assert len(rows) == 23
            counts[kind] = {"known": sum(x["value"] != "UNKNOWN" for x in rows),
                            "evidence_backed_known": sum(x["value"] != "UNKNOWN" and bool(x["evidence"]) for x in rows),
                            "unknown": sum(x["value"] == "UNKNOWN" for x in rows),
                            "high_confidence": sum(x["confidence"] == "high" for x in rows)}
        m = metrics[fid]
        report["features"].append({"feature_id": fid, "name": f["name"], "known_by_snapshot": counts,
                                   "exact_agreement_pct": m["exact_agreement_pct"],
                                   "unknown_status_agreement_pct": m["unknown_status_agreement_pct"],
                                   "both_unknown_count": m["both_unknown_count"],
                                   "major_disagreement_pct": m["major_disagreement_pct"],
                                   "major_disagreement_count": len(m["major_disagreements"]),
                                   "one_unknown_disagreement_count": len(m["one_unknown_disagreements"]),
                                   "known_to_unknown_transitions": len(temporal[fid]["known_to_unknown"]),
                                   "ambiguity": ambiguity, "verdict": verdict,
                                   "direct_jev_after_revision": typ, "history_state": history,
                                   "deterministic_code": code, "minimum_input": minimum})
        cells = [f"{counts[k]['known']}/23 ({counts[k]['evidence_backed_known']})" for k in KINDS]
        table.append(f"| {fid} | {' | '.join(cells)} | {m['exact_agreement_pct']}% | {ambiguity} | {verdict} |")
        jev += [f"## {fid} — {f['name']}", "", f"**Вердикт:** {verdict}. Напрямую отдавать Jev сейчас: нет; после уточнения — `{typ}`.", "",
                f"**История/состояние:** {history}. **Логика в коде:** {code}.", "",
                f"**Минимальный вход:** {minimum}.", "",
                f"**Проблема разметки:** {ambiguity}. Точное согласие {m['exact_agreement_pct']}%; содержательных расхождений {len(m['major_disagreements'])}/23.", ""]
        if fid == "R01":
            jev += ["**Правило после уточнения.** Уровень 2 требует одновременно: ответственную роль клиента, её конкретное действие и ограниченную контрольную точку. Разрозненные упоминания руководителя, звонка продавца и общей надежды на решение не складываются в уровень 2. Уровень 1 — названная роль или барьер без полного набора. Уровень 0 допустим лишь после содержательного обсуждения процесса решения, где процесс не назван; при отсутствии такого разговора нужен UNKNOWN. Если возникает новый gate, классифицировать актуальный gate на дату среза, сохранив ссылку на исходную реплику. Это адресует 8/23 содержательных расхождений и ход 2→1 в одной сделке.", ""]
        if fid == "R02":
            jev += ["**Минимальное состояние для Jev/NeuroROP.** Хранить список клиентских обязательств с полями `commitment_id`, `agreed_at`, `customer_owner`, `promised_action`, `due_at` либо ожидаемый результат, `replaces_id`, `completion_evidence_at`. Jev извлекает из новых сообщений, было ли обещание конкретным и что клиент сообщил о выполнении/переносе. Код выбирает последнее действующее обязательство, сравнивает `due_at` со временем среза и считает явно пропущенные сроки. Значение «неоднократно сорван» требует минимум двух подтверждённых пропусков без новой конкретной замены; отсутствие записи о выполнении само по себе не равно пропуску. Если срок или статус неизвестен, ставить UNKNOWN; «шаг не согласован» — только при достаточном охвате обсуждения. После нового обещания прежний статус остаётся в истории, а метка отражает текущий шаг. Так устраняется необходимость для Jev самому считать даты и помнить всю историю.", ""]
    table += ["", "Согласие рассчитано на независимой контрольной подвыборке из 23 срезов (20% всех 115). `UNKNOWN agreement` и случаи расхождения доступны в `reliability/agreement.json`. Все вердикты относятся к воспроизводимости разметки, не к связи с исходом сделки.", ""]
    (HERE / "feature_labelability.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "feature_labelability.md").write_text("\n".join(table), encoding="utf-8")
    (HERE / "jev_design_notes.md").write_text("\n".join(jev), encoding="utf-8")
    temporal_md = ["# Временное поведение меток", "",
                   "Переходы проверены по фактическому времени cutoff. В 8 из 23 сделок порядок D3/D7/T25/T50/T80 не является календарным: процентный срез короткой сделки наступает раньше фиксированного дня. Поэтому последовательности ниже берутся из `temporal_data.json` в хронологическом порядке.", "",
                   "`Первое подтверждение` означает первое значение не `UNKNOWN` со ссылкой на событие. Ответы об отсутствии признака без события отдельно не считаются подтверждением.", "",
                   "| ID | Первое подтверждение: D3 / D7 / T25 / T50 / T80 / никогда | Переходы известно→UNKNOWN | Замечание |",
                   "|---|---|---:|---|"]
    notes = {
        "R01": "8/23 контрольных разногласий по содержательному уровню; в 18745 отмечен ход 0→2→1→2, возможно сменился gate или не определено, что считать текущим.",
        "R02": "7 переходов известно→UNKNOWN; статус последнего шага меняется при новом обещании, требуется хранить историю и момент срока.",
        "R03": "Уровень достаточности обычно сохраняется, но порог зависит от задачи.",
        "R04": "1 переход известно→UNKNOWN и 5/23 разногласий UNKNOWN против значения; нужна граница отсутствия сведений.",
        "R05": "1 переход известно→UNKNOWN; новая область применения может вновь открыть вопрос применимости.",
        "R06": "В 6983 и 7243 значение «Да» позже стало «Нет»; нужна версия актуальной конфигурации и правило отзыва согласия.",
        "R07": "В 18485 «Да» сменилось на «Нет» при более позднем cutoff, хотя факт прошлого обращения должен сохраняться; проверить правило накопления.",
        "R08": "Положительный факт сравнения не исчезал, но 7/23 содержательных разногласий по самому критерию.",
        "R09": "Появляется позднее; 1 переход известно→UNKNOWN, формальная стадия должна иметь явный источник и время.",
        "R10": "1 переход известно→UNKNOWN; предпочтение может устареть, нужна актуальность высказывания."
    }
    cutoffs = {(x["deal_id"], x["snapshot"]): datetime.fromisoformat(x["cutoff"]) for x in manifest["snapshots"]}
    for fid in sorted(temporal):
        first = Counter()
        for seq in temporal[fid]["sequences"]:
            deal = seq["deal_id"]
            first_kind = next((kind for kind in sorted(KINDS, key=lambda k: (cutoffs[deal, k], KINDS.index(k)))
                               if labels[deal, kind, fid]["value"] != "UNKNOWN" and labels[deal, kind, fid]["evidence"]), None)
            first[first_kind or "never"] += 1
        temporal_md.append(f"| {fid} | {' / '.join(str(first[k]) for k in (*KINDS, 'never'))} | {len(temporal[fid]['known_to_unknown'])} | {notes[fid]} |")
    temporal_md += ["", "Нестабильность метки не доказывает изменение поведения клиента: часть переходов вызвана смешением «текущее состояние» и «когда-либо происходило», а также датированными задним числом worklog-записями. Два агрегированных комментария с будущими обновлениями исключены из производных срезов. Для одной короткой сделки из D7 удалено окончательное решение клиента и последующая переписка.", ""]
    (HERE / "temporal_behavior.md").write_text("\n".join(temporal_md), encoding="utf-8")
    reliable = """# Краткий итог Validation 2A

Размечены 115 слепых срезов 23 сделок по 10 замороженным признакам: 1150 основных меток. Независимый Luna Max worker повторно разметил 23 среза (20%), 230 меток. Ни один разметчик не получал метку исхода; сравнения классов и прогностической проверки не было. Значения, время и ссылки на события прошли проверку.

**Без изменений ни один признак пока не признан достаточно однозначным для передачи в holdout.** Ближайшие к следующему этапу после точечных правок: R02 (87,0% точного согласия, но требуется разделить смысл обещания и расчёт истории), R04 (73,9%; лишь 1/23 содержательное расхождение, зато 5/23 споров UNKNOWN/значение) и R03 (73,9%; нужен критерий достаточности входных данных). Это очередь на доработку, не подтверждение пригодности уже сейчас.

Самая слабая воспроизводимость у R07 (56,5% точного согласия) и R01 (65,2%). Для R01 разметчики 8 раз из 23 расходились между содержательными уровнями, прежде всего «роль/барьер назван» и «есть ответственный шаг с контрольной точкой». R02 имеет 7 переходов из известного значения в UNKNOWN по мере движения времени: для его разметки нужен журнал последнего клиентского обязательства, срока и факта выполнения. R07 требует отдельно определять инициатора по каналу и смысл обращения по содержанию.

На D3 значение без UNKNOWN получили почти все признаки, но это часто отрицательный ответ без положительной ссылки на событие. Например, у R01 на D3 22/23 значений, лишь 5 подкреплены событием; у R08 — 22/23 и только 2. Поэтому эти доли нельзя трактовать как раннее появление содержательного сигнала. Более предметно уже на D3 доступны R02 (15 событийно подкреплённых значений), R03 (18) и R04 (10). R06, R08, R09 и R10 чаще получают прямые подтверждения позднее; R09 особенно зависит от стадии.

Ограничения: небольшая контрольная выборка, различный охват каналов, worklog-записи с датой без времени и отдельные агрегированные записи с будущими обновлениями. Границы T25/T50/T80 вычислены из целого `life_days`, поэтому точность срезов ограничена сутками. Для короткой сделки D7 охватывает предшествующую решению историю после удаления самого решения.

Следующее действие — уточнить правила `UNKNOWN`, пороги R01/R03/R04 и разделение Jev/кода в R02/R07, затем повторить проверку воспроизводимости на слепых срезах. Holdout validation в этом запуске не выполнялась.
"""
    (HERE / "executive_summary.md").write_text(reliable, encoding="utf-8")
    files = ["build_snapshots.py", "analyze_labels.py", "finalize.py", "labeling_contract.json", "labeling_assignment.json", "snapshot_manifest.json", "reliability/sample.json", "reliability/second_labels.json", "reliability/agreement.json", "temporal_data.json", "feature_labelability.json", "feature_labelability.md", "temporal_behavior.md", "jev_design_notes.md", "executive_summary.md", "run_manifest.json", "labels/A.json", "labels/B.json", "labels/C.json"]
    run = {"run_version": "validation_2a", "primary_model_selected": "GPT-6 (exact selected variant not exposed to this agent)",
           "workers": "gpt-6-luna, max (three primary labelers and one independent reliability labeler)",
           "deal_count": 23, "snapshot_count": 115, "primary_label_count": 1150,
           "reliability_sample_count": 23, "reliability_label_count": 230,
           "source_catalog_frozen": "research_outputs/discovery_v1/feature_candidates.json",
           "outcome_used": False, "primary_inspected_raw_timeline": False,
           "input_issues": manifest["input_issues"],
           "exclusions": {"terminal_content_limit": manifest["blind_content_limits"], "embedded_future_events": manifest["excluded_embedded_future_events"], "stage_changes": "all excluded"},
           "worker_failures_fallbacks": ["Worker C initial evidence pointers for one deal were corrected against its snapshots before analysis."],
           "outputs_produced": files + [str(x.relative_to(HERE)).replace("\\", "/") for x in (HERE / "snapshots").glob("*.json")],
           "timestamp": datetime.now().astimezone().isoformat()}
    (HERE / "run_manifest.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    assert len(report["features"]) == 10 and all((HERE / file).exists() for file in files)


if __name__ == "__main__":
    main()
