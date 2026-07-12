from pathlib import Path

from locallore.parser import parse_record


def test_parser_extracts_text_blocks_and_tolerates_unknown_fields() -> None:
    parsed = parse_record(
        {"sessionId": "s", "extra": True, "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]}},
        Path("session.jsonl"),
        1,
    )
    assert parsed is not None
    assert parsed.text == "hello"
    assert parsed.session_id == "s"


def test_parser_ignores_unrecognized_records() -> None:
    assert parse_record({"type": "progress"}, Path("session.jsonl"), 1) is None
