"""Tests for the plain-text interactive fallback."""

from __future__ import annotations

from unittest.mock import patch

import questionary

from fixpm.interactive import choose
from fixpm.rules.base import Correction, IssueKind


def _correction(command: str, score: float = 0.9) -> Correction:
    return Correction(
        command=command,
        kind=IssueKind.SUBCOMMAND_TYPO,
        score=score,
        message=f"did you mean `{command}`?",
    )


def test_choose_falls_back_to_plain_menu_when_questionary_cannot_render():
    corrections = [_correction("npm install react")]

    with patch.object(questionary, "select", side_effect=RuntimeError("no console buffer")):
        with patch("builtins.input", return_value="1"):
            result = choose(corrections)

    assert result is corrections[0]


def test_plain_menu_skip_returns_none():
    corrections = [_correction("npm install react")]

    with patch.object(questionary, "select", side_effect=RuntimeError("no console buffer")):
        with patch("builtins.input", return_value="2"):  # last option = Skip
            result = choose(corrections)

    assert result is None


def test_plain_menu_reprompts_on_invalid_input():
    corrections = [_correction("npm install react")]

    with patch.object(questionary, "select", side_effect=RuntimeError("no console buffer")):
        with patch("builtins.input", side_effect=["nope", "99", "1"]):
            result = choose(corrections)

    assert result is corrections[0]
