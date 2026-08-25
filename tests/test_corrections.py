"""End-to-end correction tests over the full pipeline (detector + rules)."""

from __future__ import annotations

import pytest

from fixpm.corrector import get_corrections
from fixpm.rules.base import IssueKind

CASES: list[tuple[str, str, IssueKind | None]] = [
    # --- npm ---------------------------------------------------------------
    ("npm isntall react", "npm install react", IssueKind.SUBCOMMAND_TYPO),
    ("npm instal", "npm install", None),
    ("npm innit -y", "npm init -y", None),
    ("npm i loadash", "npm i lodash", IssueKind.PACKAGE_TYPO),
    ("npm i loadads", "npm i lodash", IssueKind.PACKAGE_TYPO),
    ("npm install express save-dev",
     "npm install express --save-dev", IssueKind.MISSING_DASHES),
    ("npm install --svae express",
     "npm install --save express", IssueKind.FLAG_TYPO),
    ("npm run", "npm run <script>", IssueKind.ARG_REQUIRED),
    ("npm --hepl install", "npm --help install", IssueKind.FLAG_TYPO),
    ("npm run-scirpt dev", "npm run-script dev", None),
    # --- pnpm / yarn (baseline coverage) ------------------------------------
    ("pnpm isntall", "pnpm install", None),
    ("pnpm ad left-pad", "pnpm add left-pad", IssueKind.SUBCOMMAND_TYPO),
    ("yarn isntall", "yarn install", None),
    ("yarn globla add vite", "yarn global add vite", None),
    ("yarn global ad typescript",
     "yarn global add typescript", IssueKind.SUBCOMMAND_TYPO),
    # --- npx (package-first) -----------------------------------------------
    ("npx creat-react-app web",
     "npx create-react-app web", IssueKind.PACKAGE_TYPO),
    ("npx cerate-react-app my-app",
     "npx create-react-app my-app", IssueKind.PACKAGE_TYPO),
    ("npx creaet-react-app my-app",
     "npx create-react-app my-app", IssueKind.PACKAGE_TYPO),
    ("npx vite-templat my-app",
     "npx create-vite my-app", IssueKind.PACKAGE_TYPO),
]


@pytest.mark.parametrize(("text", "expected", "kind"), CASES)
def test_suggests_fix(patched_client, text: str, expected: str,
                      kind: IssueKind | None) -> None:
    corrections = get_corrections(text)
    commands = [c.command for c in corrections]
    assert expected in commands, f"expected {expected!r} in {commands}"
    if kind is not None:
        assert kind in [c.kind for c in corrections]


NO_FIX = [
    "git push --force",
    "npm",
    "npm -v",
    "npm i react",
    "npm install express --save-dev",
    "npm run build -- --watch",
    "pnpm add vite",
    "yarn add vite",
    "npx cowsay hi",
]


@pytest.mark.parametrize("text", NO_FIX)
def test_valid_commands_left_alone(patched_client, text: str) -> None:
    assert get_corrections(text) == []


def test_max_three_suggestions(patched_client) -> None:
    corrections = get_corrections("npm isntall react")
    assert 1 <= len(corrections) <= 3


def test_scores_sorted_desc(patched_client) -> None:
    corrections = get_corrections("npm isntall react")
    scores = [c.score for c in corrections]
    assert scores == sorted(scores, reverse=True)
