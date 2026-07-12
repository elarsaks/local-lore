from pathlib import Path

from locallore.parser import parse_record


def test_assistant_message_text_is_extracted_from_content_blocks() -> None:
    parsed = parse_record(
        {"sessionId": "s", "extra": True, "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]}},
        Path("session.jsonl"),
        1,
    )
    assert parsed is not None
    assert parsed.text == "hello"
    assert parsed.session_id == "s"


def test_non_message_records_are_ignored() -> None:
    assert parse_record({"type": "progress"}, Path("session.jsonl"), 1) is None


def test_tool_use_extracts_a_structured_file_operation() -> None:
    parsed = parse_record(
        {
            "sessionId": "s",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "src/search.py"},
                    }
                ],
            },
        },
        Path("session.jsonl"),
        1,
    )

    assert parsed is not None
    assert parsed.file_operations == (("src/search.py", "edit"),)
