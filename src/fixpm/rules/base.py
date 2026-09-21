"""Core data model shared by all rule tables and the detection engine.

Adding support for a new CLI means building a ``ManagerSpec`` and calling
:func:`register` on it — no engine changes required. The class name predates
non-package-manager specs (git, docker, cargo, go, pip); it describes any CLI
with subcommands. See any module in ``fixpm.rules`` for a worked example.

Coverage is opt-in per field, and empty means "do not validate":
``flags`` empty skips flag checking, ``arg_required`` empty never reports a
missing argument. That is why the non-npm specs leave both empty — a partial
allow-list would flag valid input as wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IssueKind(str, Enum):
    SUBCOMMAND_TYPO = "subcommand-typo"
    FLAG_TYPO = "flag-typo"
    MISSING_DASHES = "missing-dashes"
    ARG_REQUIRED = "argument-required"
    PACKAGE_TYPO = "package-typo"


KIND_LABEL: dict[IssueKind, str] = {
    IssueKind.SUBCOMMAND_TYPO: "command fix",
    IssueKind.FLAG_TYPO: "flag fix",
    IssueKind.MISSING_DASHES: "missing --",
    IssueKind.ARG_REQUIRED: "missing argument",
    IssueKind.PACKAGE_TYPO: "package fix",
}


@dataclass(frozen=True)
class Issue:
    """One detected problem inside a failed command line."""

    kind: IssueKind
    token: str
    index: int  # absolute index into the full token list
    message: str
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Correction:
    """A concrete replacement command offered to the user."""

    command: str
    kind: IssueKind
    score: float  # 0..1 confidence
    message: str
    executable: bool = True  # False when the fix needs manual arguments


@dataclass(frozen=True)
class ManagerSpec:
    """Declarative rule table describing one package-manager CLI.

    Fields are intentionally plain data so contributors can extend coverage
    without touching the engine:

    commands         canonical top-level subcommands
    aliases          alternate spellings -> canonical command
    flags            validated flags per canonical command (partial is fine:
                     unlisted commands simply skip flag validation)
    global_flags     flags valid anywhere
    value_flags      flags that consume the following token
    package_commands commands whose positional args are package names
    arg_required     commands that fail without a positional argument
    typo_hints       curated misspelling -> correct token (overrides distance).
                     Consulted in the command slot and in the chain-verb slot;
                     an entry only applies where its target is valid, so one
                     map can serve both (see detector._hinted). Needed for
                     short transpositions (``ud`` -> ``up``), which score
                     0.667 and fall under every similarity floor.
    chains           chain command -> its second-level verbs. `yarn global add`,
                     `docker container ls`, `go mod tidy` and `pip cache purge`
                     all put a verb after the chain command; declaring that
                     closed verb set here is what lets the engine validate the
                     slot (and fix a typo in it) without knowing the CLI. A
                     command absent from this map is treated as a plain
                     subcommand and its args are never matched against verbs.
    package_first    npx-style CLIs whose first positional is a package
    subcommand_min_score  similarity floor for accepting a subcommand typo.
                     Lower it for closed vocabularies (npm's command space is
                     fixed); raise it for CLIs with a plugin namespace, where
                     an unlisted-but-valid command (``git lfs``, ``docker
                     buildx``, ``cargo nextest``) must not be reported as a
                     typo of whatever it happens to resemble.
    """

    name: str
    binaries: tuple[str, ...]
    commands: tuple[str, ...] = ()
    aliases: dict[str, str] = field(default_factory=dict)
    flags: dict[str, tuple[str, ...]] = field(default_factory=dict)
    global_flags: tuple[str, ...] = ()
    value_flags: tuple[str, ...] = ()
    package_commands: tuple[str, ...] = ()
    arg_required: tuple[str, ...] = ()
    typo_hints: dict[str, str] = field(default_factory=dict)
    chains: dict[str, tuple[str, ...]] = field(default_factory=dict)
    package_first: bool = False
    subcommand_min_score: float = 0.55

    @property
    def vocabulary(self) -> set[str]:
        return set(self.commands) | set(self.aliases)

    def canonical(self, token: str) -> str | None:
        if token in self.commands:
            return token
        return self.aliases.get(token)


_REGISTRY: dict[str, ManagerSpec] = {}


def register(spec: ManagerSpec) -> ManagerSpec:
    _REGISTRY[spec.name] = spec
    return spec


def spec_for_binary(binary: str) -> ManagerSpec | None:
    return next((s for s in _REGISTRY.values() if binary in s.binaries), None)


def all_specs() -> list[ManagerSpec]:
    return list(_REGISTRY.values())
