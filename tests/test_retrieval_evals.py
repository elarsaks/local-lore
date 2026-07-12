from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from locallore.db import connect, migrate
from locallore.importer import import_sessions
from locallore.search import get_context, search_messages

ROOT = Path(__file__).parents[1]
SUITE_PATH = ROOT / "evals" / "retrieval.yaml"
FIXTURES = ROOT / "evals" / "fixtures" / "keyword-sessions"


def load_cases() -> list[dict[str, object]]:
    suite = yaml.safe_load(SUITE_PATH.read_text())
    assert suite["version"] == 1
    assert suite["name"] == "keyword_retrieval"
    return suite["cases"]


@pytest.fixture
def eval_database(tmp_path: Path):
    connection = connect(tmp_path / "retrieval-eval.db")
    migrate(connection)
    result = import_sessions(connection, FIXTURES)
    assert result.errors == 0
    yield connection
    connection.close()


def test_retrieval_suite_has_unique_cases_and_no_model_configuration() -> None:
    raw_suite = SUITE_PATH.read_text().lower()
    cases = load_cases()

    assert len(cases) >= 6
    assert len({case["id"] for case in cases}) == len(cases)
    assert "api_key" not in raw_suite
    assert "model:" not in raw_suite
    assert "judge" not in raw_suite


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_keyword_retrieval_case(case: dict[str, object], eval_database) -> None:
    expected = case["expected"]
    response = search_messages(
        eval_database,
        case["query"],
        **case.get("filters", {}),
    )
    returned_ids = [result["message_id"] for result in response["results"]]

    if top_message := expected.get("top_message"):
        assert returned_ids[0] == top_message
    assert set(expected["relevant_messages"]) <= set(returned_ids)
    assert set(expected.get("excluded_messages", [])).isdisjoint(returned_ids)

    if context_case := expected.get("context"):
        context = get_context(
            eval_database,
            context_case["session_id"],
            context_case["message_id"],
            before=context_case["before"],
            after=context_case["after"],
        )
        assert [message["message_id"] for message in context["messages"]] == (
            context_case["message_ids"]
        )
