"""Arrow-key interactive selection (questionary / prompt_toolkit)."""

from __future__ import annotations

import questionary
from questionary import Choice

from .rules.base import KIND_LABEL, Correction


def choose(corrections: list[Correction]) -> Correction | None:
    choices = [
        Choice(
            title=f"{c.command}   · {KIND_LABEL[c.kind]} · {int(c.score * 100)}%",
            value=c,
        )
        for c in corrections
    ]
    choices.append(Choice(title="Skip — do nothing", value=None))
    try:
        return questionary.select(
            "Apply a fix:",
            choices=choices,
            qmark="?",
            instruction="(↑/↓ move · enter select · ctrl+c cancel)",
        ).ask()
    except (KeyboardInterrupt, EOFError):
        return None
