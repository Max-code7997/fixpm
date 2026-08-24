"""Turn analyzer issues into concrete, ranked replacement commands."""

from __future__ import annotations

import shlex

from .detector import analyze, tokenize
from .distance import similarity
from .packages import NpmRegistry, base_name, format_downloads
from .rules.base import Correction, Issue, IssueKind, ManagerSpec

_client: NpmRegistry | None = None

# Placeholder shown when a fix needs manual input (never auto-executed).
_PLACEHOLDERS = {
    "run": "<script>",
    "exec": "<package> [args...]",
    "dlx": "<package> [args...]",
    "add": "<package>",
    "install": "<package>",
    "remove": "<package>",
    "uninstall": "<package>",
    "why": "<package>",
    "info": "<package>",
    "create": "<initializer>",
    "config": "<key> <value>",
    "cache": "<action>",
    "pkg": "<action>",
}


def _default_client() -> NpmRegistry:
    global _client
    if _client is None:
        _client = NpmRegistry()
    return _client


def get_corrections(
    text: str,
    *,
    spec: ManagerSpec | None = None,
    client: NpmRegistry | None = None,
) -> list[Correction]:
    """Top fix suggestions (max 3), best first."""
    tokens, spec, issues = analyze(text, spec)
    if spec is None or not issues:
        return []
    client = client or _default_client()
    corrections: list[Correction] = []
    for issue in issues:
        corrections.extend(_fix_issue(tokens, spec, issue, client))
    best: dict[str, Correction] = {}
    for c in corrections:
        if c.command not in best or c.score > best[c.command].score:
            best[c.command] = c
    ranked = sorted(best.values(), key=lambda c: (-c.score, c.command))
    return ranked[:3]


def _ratio_score(ratio: float) -> float:
    return round(0.5 + 0.45 * ratio, 3)


def _replace(tokens: list[str], index: int, new_token: str) -> str:
    patched = list(tokens)
    patched[index] = new_token
    return shlex.join(patched)


def _fix_issue(tokens: list[str], spec: ManagerSpec, issue: Issue,
               client: NpmRegistry) -> list[Correction]:
    kind = issue.kind

    if kind is IssueKind.SUBCOMMAND_TYPO:
        out = []
        hinted = spec.typo_hints.get(issue.token.lower())
        for cand in issue.candidates[:3]:
            score = (0.95 if cand == hinted
                     else _ratio_score(similarity(issue.token.lower(), cand)))
            out.append(Correction(_replace(tokens, issue.index, cand),
                                  kind, score, issue.message))
        return out

    if kind is IssueKind.FLAG_TYPO:
        return [
            Correction(_replace(tokens, issue.index, cand), kind,
                       _ratio_score(similarity(issue.token, cand)),
                       issue.message)
            for cand in issue.candidates[:2]
        ]

    if kind is IssueKind.MISSING_DASHES:
        return [Correction(_replace(tokens, issue.index, issue.candidates[0]),
                           kind, 0.9, issue.message)]

    if kind is IssueKind.ARG_REQUIRED:
        placeholder = _PLACEHOLDERS.get(issue.token, "<arguments>")
        return [Correction(f"{shlex.join(tokens)} {placeholder}", kind, 0.6,
                           issue.message, False)]

    if kind is IssueKind.PACKAGE_TYPO:
        name = base_name(issue.token)
        out = []
        for s in client.suggest(name)[:3]:
            if s.name.lower() == name.lower():
                continue
            new_token = issue.token.replace(name, s.name, 1)
            detail = (f"package '{name}' -> '{s.name}' "
                      f"({format_downloads(s.weekly_downloads)}/week)")
            out.append(Correction(_replace(tokens, issue.index, new_token),
                                  kind, s.score, detail))
        return out

    return []


__all__ = ["get_corrections", "tokenize"]
