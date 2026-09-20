"""Arrow-key interactive selection (questionary / prompt_toolkit), with a
plain-text numbered-menu fallback for terminals prompt_toolkit can't drive
(e.g. some CI runners, IDE-embedded terminals, or a TERM mismatch on
Windows that trips prompt_toolkit's console-buffer detection)."""

from __future__ import annotations

import questionary
import typer
from questionary import Choice

from .rules.base import KIND_LABEL, Correction


def _choose_plain(corrections: list[Correction]) -> Correction | None:
    """Numbered-menu fallback: no cursor movement, just type a number.

    Kept ASCII-only on purpose — this path exists specifically for terminals
    that couldn't handle prompt_toolkit's rendering, and non-ASCII
    separators (the middle dot / em dash used in the rich menu) are exactly
    the kind of thing that turns into mojibake under a non-UTF-8 Windows
    console code page (e.g. cp936).
    """
    typer.echo("Apply a fix:")
    for i, c in enumerate(corrections, start=1):
        typer.echo(f"  {i}) {c.command}   - {KIND_LABEL[c.kind]} - {int(c.score * 100)}%")
    skip_index = len(corrections) + 1
    typer.echo(f"  {skip_index}) Skip - do nothing")

    while True:
        try:
            raw = input(f"Enter a number [1-{skip_index}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            return None
        if not raw.isdigit():
            typer.echo("Please enter a number.")
            continue
        choice_num = int(raw)
        if choice_num == skip_index:
            return None
        if 1 <= choice_num <= len(corrections):
            return corrections[choice_num - 1]
        typer.echo(f"Please enter a number between 1 and {skip_index}.")


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
    except Exception:
        # prompt_toolkit couldn't drive this terminal (e.g.
        # NoConsoleScreenBufferError on Windows when TERM claims xterm
        # but there's no real console buffer). Degrade instead of crashing.
        return _choose_plain(corrections)
