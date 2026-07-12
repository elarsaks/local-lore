from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parents[1]
EVAL_PATH = ROOT / "evals" / "remember.yaml"
REQUIRED_BEHAVIORS = {
    "search_before_answering",
    "synthesize_evidence",
    "cite_useful_provenance",
    "distinguish_inference",
    "fetch_context_if_needed",
    "report_no_reliable_memory",
    "do_not_invent_evidence",
}


def load_eval_cases() -> list[dict[str, object]]:
    suite = yaml.safe_load(EVAL_PATH.read_text())

    assert suite["version"] == 1
    assert suite["name"] == "remember_contract"
    return suite["cases"]


def test_remember_eval_suite_has_unique_cases_and_complete_coverage() -> None:
    cases = load_eval_cases()
    case_ids = [case["id"] for case in cases]
    covered_behaviors = {
        behavior
        for case in cases
        for behavior in case["expected"]["behaviors"]
    }

    assert len(cases) >= 6
    assert len(case_ids) == len(set(case_ids))
    assert covered_behaviors == REQUIRED_BEHAVIORS


@pytest.mark.parametrize("case", load_eval_cases(), ids=lambda case: case["id"])
def test_remember_eval_case_is_well_formed(case: dict[str, object]) -> None:
    expected = case["expected"]

    assert case["prompt"].strip()
    assert expected["initial_query"] == case["prompt"]
    assert isinstance(expected["prefer_current_project"], bool)
    assert isinstance(expected["filters"], dict)
    assert expected["behaviors"]
    assert set(expected["behaviors"]) <= REQUIRED_BEHAVIORS


def test_remember_surfaces_encode_the_eval_contract() -> None:
    command = (ROOT / "commands" / "remember.md").read_text().lower()
    skill = (ROOT / "skills" / "remember" / "SKILL.md").read_text().lower()
    surfaces = f"{command}\n{skill}"

    required_language = (
        "before answering",
        "user's wording",
        "current project",
        "date",
        "file filters",
        "context only when",
        "synthesize",
        "evidence from inference",
        "no reliable memory",
        "not ground truth",
    )
    for phrase in required_language:
        assert phrase in surfaces

