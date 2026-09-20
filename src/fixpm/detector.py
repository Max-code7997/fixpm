"""Classify what went wrong in a failed package-manager command line.

One generic engine consumes every ``ManagerSpec``; per-manager knowledge lives
entirely in the rule tables under ``fixpm.rules``.
"""

from __future__ import annotations

import re
import shlex

from .distance import rank
from .rules import spec_for_binary
from .rules.base import Issue, IssueKind, ManagerSpec

_PKG_RE = re.compile(
    r"^(@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$", re.IGNORECASE
)


def tokenize(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def looks_like_package(token: str) -> bool:
    """Conservative npm-package-name shape check (paths, globs and files out)."""
    if not token or any(c in token for c in "*~=\\"):
        return False
    if token.startswith((".", "~")):
        return False
    if "/" in token and not token.startswith("@"):
        return False
    return bool(_PKG_RE.match(token))


def _nearest(token: str, pool: tuple[str, ...], top: int = 2,
             min_score: float = 0.6) -> list[str]:
    return [c for c, _ in rank(token.lower(), [p.lower() for p in sorted(pool)],
                               top=top, min_score=min_score)]


def _sub_candidates(token: str, spec: ManagerSpec) -> list[str]:
    hint = spec.typo_hints.get(token.lower())
    if hint:
        return [hint]
    return _nearest(token, tuple(spec.vocabulary), top=3, min_score=0.55)


def analyze(
    text: str, spec: ManagerSpec | None = None
) -> tuple[list[str], ManagerSpec | None, list[Issue]]:
    """Return ``(tokens, spec_or_None, issues)`` for a failed command line."""
    tokens = tokenize(text)
    located = _locate(tokens, spec)
    if located is None:
        return tokens, None, []
    index, spec = located
    if spec.package_first:
        return tokens, spec, _analyze_package_first(spec, tokens, index + 1)
    return tokens, spec, _analyze_subcommand(spec, tokens, index + 1)


def _locate(tokens: list[str],
            spec: ManagerSpec | None) -> tuple[int, ManagerSpec] | None:
    if spec is not None:
        for i, t in enumerate(tokens[:4]):
            if t in spec.binaries:
                return i, spec
        return None
    for i, t in enumerate(tokens[:4]):
        found = spec_for_binary(t)
        if found is not None:
            return i, found
    return None


def _analyze_subcommand(spec: ManagerSpec, tokens: list[str],
                        start: int) -> list[Issue]:
    issues: list[Issue] = []
    rest = tokens[start:]

    # Leading global flags, e.g. `npm --prefix ./x install`
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        flag = rest[i]
        if flag in spec.value_flags and i + 1 < len(rest):
            i += 2
            continue
        if flag not in spec.global_flags:
            near = _nearest(flag, spec.global_flags)
            if near:
                issues.append(Issue(
                    IssueKind.FLAG_TYPO, flag, start + i,
                    f"Unknown global flag '{flag}' — did you mean {near[0]}?",
                    tuple(near),
                ))
        i += 1

    if i >= len(rest):
        return issues

    sub = rest[i]
    sub_abs = start + i
    canon = spec.canonical(sub)

    if canon is None:
        candidates = _sub_candidates(sub, spec)
        if candidates:
            issues.append(Issue(
                IssueKind.SUBCOMMAND_TYPO, sub, sub_abs,
                f"'{sub}' is not a {spec.name} command",
                tuple(candidates),
            ))
        # One fix at a time: stop validating after an unknown command.
        return issues

    # Chain commands like `yarn global add <pkg>` — absorb the sub-verb.
    # The sub-verb slot gets typo tolerance too: `yarn global ad x` must
    # still resolve the chain (and report the typo) instead of falling apart.
    extra = 0
    if canon == "global" and spec.sub_verbs and i + 1 < len(rest):
        nxt = rest[i + 1]
        if nxt in spec.sub_verbs:
            extra = 1
            canon = f"global {nxt}"
        else:
            near = _nearest(nxt, spec.sub_verbs, top=1, min_score=0.55)
            if near:
                issues.append(Issue(
                    IssueKind.SUBCOMMAND_TYPO, nxt, start + i + 1,
                    f"'{nxt}' is not a {spec.name} subcommand of 'global'",
                    tuple(near),
                ))
                extra = 1
                canon = f"global {near[0]}"
    effective = canon.rsplit(" ", 1)[-1]
    allowed = spec.flags.get(effective, ())

    positional: list[tuple[int, str]] = []
    j = i + 1 + extra
    while j < len(rest):
        token = rest[j]
        if token == "--":  # passthrough separator: everything after is exempt
            break
        if token.startswith("-"):
            if allowed and token not in allowed and token not in spec.global_flags:
                near = _nearest(token, allowed)
                if near:
                    issues.append(Issue(
                        IssueKind.FLAG_TYPO, token, start + j,
                        f"Unknown flag '{token}' for `{spec.name} "
                        f"{effective}` — did you mean {near[0]}?",
                        tuple(near),
                    ))
            if token in spec.value_flags:
                j += 1  # skip the consumed value
        else:
            positional.append((j, token))
        j += 1

    # `npm install express save-dev` -> missing dashes on `save-dev`
    dashless = {f.lstrip("-"): f for f in allowed}
    flagged: set[int] = set()
    for jj, token in positional:
        if len(token) > 1 and token in dashless:
            issues.append(Issue(
                IssueKind.MISSING_DASHES, token, start + jj,
                f"Missing flag prefix — did you mean {dashless[token]}?",
                (dashless[token],),
            ))
            flagged.add(jj)
    positional = [(jj, t) for jj, t in positional if jj not in flagged]

    # Only report a missing argument when nothing else was flagged. For
    # `npm uninstall save-dev` the real problem is the missing dashes, and
    # pairing it with "needs an argument" emitted a second suggestion that
    # still contained the very typo the first one fixes:
    #   [missing --]       npm uninstall --save-dev
    #   [missing argument] npm uninstall save-dev <package>
    if (canon in spec.arg_required and not positional and not flagged
            and extra == 0):
        issues.append(Issue(
            IssueKind.ARG_REQUIRED, sub, sub_abs,
            f"`{spec.name} {sub}` needs an argument "
            f"(see `{spec.name} help {effective}`)",
            (),
        ))

    if canon in spec.package_commands or canon.startswith("global "):
        checked = 0
        for jj, token in positional:
            if checked >= 2:
                break
            if token.lower() in spec.vocabulary or not looks_like_package(token):
                continue
            issues.append(Issue(
                IssueKind.PACKAGE_TYPO, token, start + jj,
                f"Check package name '{token}'",
                (),
            ))
            checked += 1
    return issues


def _analyze_package_first(spec: ManagerSpec, tokens: list[str],
                           start: int) -> list[Issue]:
    issues: list[Issue] = []
    rest = tokens[start:]
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        flag = rest[i]
        if flag in spec.value_flags and i + 1 < len(rest):
            i += 2
            continue
        if flag not in spec.global_flags:
            near = _nearest(flag, spec.global_flags)
            if near:
                issues.append(Issue(
                    IssueKind.FLAG_TYPO, flag, start + i,
                    f"Unknown flag '{flag}' — did you mean {near[0]}?",
                    tuple(near),
                ))
        i += 1

    if i >= len(rest):
        issues.append(Issue(
            IssueKind.ARG_REQUIRED, spec.name, start - 1,
            f"`{spec.name}` needs a package or binary to run",
            (),
        ))
        return issues

    pkg = rest[i]
    if looks_like_package(pkg):
        issues.append(Issue(
            IssueKind.PACKAGE_TYPO, pkg, start + i,
            f"Check package name '{pkg}'",
            (),
        ))
    return issues
