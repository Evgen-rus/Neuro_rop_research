"""Read frozen events; optional email preview never changes canonical inputs."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUOTE_HELPER = Path("D:/My_dev_project/Neuro_rop_practice/bitrix/deals/email_text.py")
QUOTE_HELPER_SHA = "c7744c987ba2be552b3c228c47f849c25a75e1d8dcb08c1c8f958621a8d11a9f"


def compact_event(event, strip_quotes):
    preview = dict(event)
    if event["event_type"] == "email":
        original = event.get("content") or ""
        preview["content"] = strip_quotes(original)
        preview["reading_notice"] = {
            "canonical_content_chars": len(original),
            "quoted_or_header_suffix_not_shown": preview["content"] != original,
            "full_content_available_with_source_lines": event["source_line"],
        }
    return preview


def main():
    if sys.argv[1:] == ["--self-check"]:
        event = {"event_type": "email", "content": "new\nFrom: quote", "source_line": 7, "event_id": "x"}
        preview = compact_event(event, lambda text: text.split("\nFrom:")[0])
        assert event["content"] == "new\nFrom: quote" and preview["content"] == "new"
        assert preview["source_line"] == 7 and preview["event_id"] == "x"
        assert preview["reading_notice"]["quoted_or_header_suffix_not_shown"] is True
        call = {"event_type": "call_transcript", "content": "full", "source_line": 9}
        assert compact_event(call, lambda _: "") == call
        print("read_view self-check: PASS")
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deal_id")
    parser.add_argument("--compact-emails", action="store_true")
    parser.add_argument("--source-lines", help="comma-separated canonical source_line values; default all")
    args = parser.parse_args()
    if not args.deal_id.isdecimal() or str(int(args.deal_id)) != args.deal_id or int(args.deal_id) <= 0:
        parser.error("positive canonical deal ID required")
    selected = set(map(int, args.source_lines.split(","))) if args.source_lines else None
    strip_quotes = None
    if args.compact_emails:
        if hashlib.sha256(QUOTE_HELPER.read_bytes()).hexdigest() != QUOTE_HELPER_SHA:
            raise RuntimeError("native email reader helper changed; reading contract requires review")
        spec = importlib.util.spec_from_file_location("native_email_reader", QUOTE_HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        strip_quotes = module.strip_quoted_history
    found = set()
    for line in (HERE / "views" / f"{args.deal_id}.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        source_line = event["source_line"]
        if selected is not None and source_line not in selected:
            continue
        found.add(source_line)
        if strip_quotes:
            event = compact_event(event, strip_quotes)
        print(json.dumps(event, ensure_ascii=False))
    if selected is not None and selected != found:
        raise ValueError(f"source lines absent from frozen view: {sorted(selected - found)}")


if __name__ == "__main__":
    main()
