"""Extract unambiguous incoming text without consulting outcome labels."""
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
QUOTE = re.compile(r"(?im)^\s*(?:-{5,}|_{5,}|>{1,}|(?:from|sent|subject|to|cc|от кого|отправленные|пересылаемое сообщение|кому|тема|дата):|.{0,120}\b(?:писал\(а\)|wrote):|.{0,120}[\w.+-]+@[\w.-]+.{0,30}>:)\s*")
SIGN = re.compile(r"(?im)^\s*(?:--\s*$|с уважением[,! ]|best regards[,! ]|regards[,! ])")
SYSTEM = re.compile(r"(?i)^\s*(?:=== SYSTEM WZ ===|принято\s+(?:изображение|файл|аудиосообщение)|:f0[0-9a-f]+:|https?://|\[сегмент)")
TAG = re.compile(r"<[^>]+>")


def clean(value, event_type):
    text = html.unescape(str(value or ""))
    text = TAG.sub(" ", text).replace("\r\n", "\n").replace("\r", "\n")
    if event_type == "email":
        text = QUOTE.split(text, maxsplit=1)[0]
        text = SIGN.split(text, maxsplit=1)[0]
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()
    if not text or SYSTEM.search(text) or not re.search(r"[А-Яа-яA-Za-z0-9]", text) or re.fullmatch(r"\S+\.(?:jpg|jpeg|png|pdf|docx?|xlsx?)", text, re.I):
        return None
    if event_type == "email" and (len(text) < 5 or text.lower().startswith(("кому:", "тема:", "from:", "от кого:"))):
        return None
    return text


def main():
    rows = []
    exclusions = {}
    seen = set()
    for path in sorted((ROOT / "dataset/deals").glob("*/clean_timeline.jsonl")):
        for line_no, line in enumerate(path.open(encoding="utf-8"), 1):
            event = json.loads(line)
            if event.get("direction") != "incoming" or event.get("event_type") not in {"message", "email"}:
                continue
            value = clean(event.get("content"), event["event_type"])
            if value is None:
                exclusions["empty_system_or_unsafe_quote"] = exclusions.get("empty_system_or_unsafe_quote", 0) + 1
                continue
            signature = value.casefold()
            if signature in seen:
                exclusions["exact_duplicate"] = exclusions.get("exact_duplicate", 0) + 1
                continue
            seen.add(signature)
            source = f"{path.parent.name}:{line_no}"
            rows.append({"example_id": "J01-" + hashlib.sha256(source.encode()).hexdigest()[:12],
                         "utterance": value, "source": {"deal_id": path.parent.name, "line": line_no,
                         "timestamp": event.get("timestamp"), "event_type": event["event_type"]}})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "candidate_pool.json").write_text(json.dumps({"source": "dataset/deals/*/clean_timeline.jsonl", "exclusions": exclusions,
        "examples": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"candidates={len(rows)} exclusions={exclusions}")


if __name__ == "__main__":
    assert clean("Размер 35 мм\n-----\nquoted", "email") == "Размер 35 мм"
    assert clean("Размер 35 мм\nвт, 5 мая 2026 г., клиент a@b.ru>:\nquoted", "email") == "Размер 35 мм"
    assert clean("=== SYSTEM WZ ===", "message") is None
    main()
