"""Classify what went wrong in a failed command line.

One generic engine consumes every ``ManagerSpec``; per-CLI knowledge lives
entirely in the rule tables under ``fixpm.rules``. The engine must never see
output of the failed command — unlike tools that re-run it to read the error,
fixpm classifies from the command line alone, which is what keeps it under
~100 ms and free of side effects.
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


def _hinted(token: str, spec: ManagerSpec, pool: set[str] | tuple[str, ...],
            ) -> str | None:
    """The curated hint for *token*, if it is valid in this slot.

    One ``typo_hints`` map feeds both the command slot and the chain-verb slot,
    so the target is checked against the slot's own vocabulary. Without that,
    a hint meant for one slot leaks into the other and suggests an invalid
    command: ``lss -> ls`` is a docker object verb, not a top-level one.
    """
    hint = spec.typo_hints.get(token.lower())
    return hint if hint is not None and hint in pool else None


def _sub_candidates(token: str, spec: ManagerSpec) -> list[str]:
    hint = _hinted(token, spec, spec.vocabulary)
    if hint is not None:
        return [hint]
    return _nearest(token, tuple(spec.vocabulary), top=3,
                    min_score=spec.subcommand_min_score)


def analyze(
    text: str, spec: ManagerSpec | None = None
) -> tuple[list[str], ManagerSpec | None, list[Issue]]:
    """Return ``(tokens, spec_or_None, issues)`` for a failed command line."""
    tokens = tokenize(text)
    located = _locate(tokens, spec)
    if located is None:
        return tokens, None, []
    index, spec = located
    if index < 0:
        # Forced table whose binary is absent from the line. Synthesise it so
        # the suggestion is a command you can actually run rather than a
        # fragment: --manager git "comit -m x" -> "git commit -m x".
        tokens = [spec.binaries[0], *tokens]
        index = 0
    if spec.package_first:
        return tokens, spec, _analyze_package_first(spec, tokens, index + 1)
    return tokens, spec, _analyze_subcommand(spec, tokens, index + 1)


def _locate(tokens: list[str],
            spec: ManagerSpec | None) -> tuple[int, ManagerSpec] | None:
    if spec is not None:
        for i, t in enumerate(tokens[:4]):
            if t in spec.binaries:
                return i, spec
        # Binary absent: -1 tells analyze() to synthesise it. Returning None
        # here made every bare fragment answer "No fix found", which left
        # --manager usable only when the binary was already in the line (and
        # then auto-detection would have found it anyway).
        return -1, spec
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

    # Chain commands like `yarn global add <pkg>`, `docker container ls` or
    # `go mod tidy` — absorb the second-level verb. Which commands chain is a
    # per-CLI fact (spec.chains), so the engine only does the lookup; the slot
    # gets typo tolerance too, because `yarn global ad x` must still resolve
    # the chain (and report the typo) instead of falling apart.
    extra = 0
    verbs = spec.chains.get(canon, ())
    if verbs and i + 1 < len(rest):
        nxt = rest[i + 1]
        if nxt in verbs:
            extra = 1
            canon = f"{canon} {nxt}"
        else:
            # Short transpositions (`ud` -> `up`, `ad` -> `add`) score 0.667
            # and land just under every similarity floor, so curated hints
            # cover them here too — validated against this slot.
            hint = _hinted(nxt, spec, verbs)
            near = [hint] if hint is not None else _nearest(
                nxt, verbs, top=1, min_score=spec.subcommand_min_score)
            if near:
                issues.append(Issue(
                    IssueKind.SUBCOMMAND_TYPO, nxt, start + i + 1,
                    f"'{nxt}' is not a {spec.name} subcommand of '{canon}'",
                    tuple(near),
                ))
                extra = 1
                canon = f"{canon} {near[0]}"
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

    # Chained package commands are listed explicitly ("global add"), so this
    # stays a plain membership test — the engine holds no idea of which chain
    # names happen to take packages.
    if canon in spec.package_commands:
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
