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
    # --- git: subcommand slot only, no flag validation ----------------------
    ("git comit -m x", "git commit -m x", IssueKind.SUBCOMMAND_TYPO),
    ("git chekcout main", "git checkout main", IssueKind.SUBCOMMAND_TYPO),
    ("git stauts", "git status", IssueKind.SUBCOMMAND_TYPO),
    ("git mrege main", "git merge main", IssueKind.SUBCOMMAND_TYPO),
    ("git puhs origin main", "git push origin main", IssueKind.SUBCOMMAND_TYPO),
    ("git revparse HEAD", "git rev-parse HEAD", IssueKind.SUBCOMMAND_TYPO),
    # --- docker / docker-compose -------------------------------------------
    ("docker contaner ls", "docker container ls", IssueKind.SUBCOMMAND_TYPO),
    ("docker buid -t x .", "docker build -t x .", IssueKind.SUBCOMMAND_TYPO),
    ("docker resta rt abc", "docker restart rt abc", IssueKind.SUBCOMMAND_TYPO),
    ("docker-compose ud", "docker-compose up", IssueKind.SUBCOMMAND_TYPO),
    ("docker-compose dwon", "docker-compose down", IssueKind.SUBCOMMAND_TYPO),
    # --- cargo / pip / go ---------------------------------------------------
    ("cargo biuld --release", "cargo build --release", IssueKind.SUBCOMMAND_TYPO),
    ("cargo tset", "cargo test", IssueKind.SUBCOMMAND_TYPO),
    ("pip instal requests", "pip install requests", IssueKind.SUBCOMMAND_TYPO),
    ("pip3 unistall requests", "pip3 uninstall requests",
     IssueKind.SUBCOMMAND_TYPO),
    ("go tset ./...", "go test ./...", IssueKind.SUBCOMMAND_TYPO),
    ("go biuld", "go build", IssueKind.SUBCOMMAND_TYPO),
    # --- second-level verbs (chain commands) --------------------------------
    # `docker <object> <verb>`, `git <cmd> <verb>`, `go <cmd> <verb>` and
    # `pip <cmd> <verb>` put a verb in the second slot; a typo there is
    # invisible to the command slot, since the command itself is known.
    ("docker container lss", "docker container ls", IssueKind.SUBCOMMAND_TYPO),
    ("docker image pruen", "docker image prune", IssueKind.SUBCOMMAND_TYPO),
    ("docker system prun", "docker system prune", IssueKind.SUBCOMMAND_TYPO),
    ("docker compose ud", "docker compose up", IssueKind.SUBCOMMAND_TYPO),
    ("docker compose dwon", "docker compose down", IssueKind.SUBCOMMAND_TYPO),
    ("docker volume creat x", "docker volume create x",
     IssueKind.SUBCOMMAND_TYPO),
    ("git remote ad origin url", "git remote add origin url",
     IssueKind.SUBCOMMAND_TYPO),
    ("git stash aplpy", "git stash apply", IssueKind.SUBCOMMAND_TYPO),
    ("git submodule updte", "git submodule update", IssueKind.SUBCOMMAND_TYPO),
    ("git worktree lst", "git worktree list", IssueKind.SUBCOMMAND_TYPO),
    ("go mod tidyy", "go mod tidy", IssueKind.SUBCOMMAND_TYPO),
    ("go mod dowload", "go mod download", IssueKind.SUBCOMMAND_TYPO),
    ("go work sycn", "go work sync", IssueKind.SUBCOMMAND_TYPO),
    ("pip cache purg", "pip cache purge", IssueKind.SUBCOMMAND_TYPO),
    ("pip config st global.index-url x",
     "pip config set global.index-url x", IssueKind.SUBCOMMAND_TYPO),
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
    # --- non-npm CLIs: unlisted-but-valid commands must stay silent ---------
    # These are the false accusations the per-spec similarity floor exists to
    # prevent: `git lfs` scores 0.667 against `ls`, `cargo nextest` 0.571
    # against `test`, `docker buildx` 0.833 against `build` (buildx is listed
    # instead, since it ships with modern docker).
    "git lfs pull",
    "git flow init",
    "cargo nextest run",
    "cargo watch -x test",
    # --- valid flags/args on the new CLIs must not be second-guessed --------
    # None of these specs declare flags, so flag validation is skipped by
    # design; an incomplete allow-list would flag valid input as wrong.
    "git commit -m x",
    "git add -A",
    "git log --oneline -5",
    "git -c core.pager=cat log",
    "git remote add origin url",
    "git rebase -i HEAD~3",
    "docker run -it --rm ubuntu bash",
    "docker compose up -d",
    "docker system prune -af",
    "docker image prune -f",
    "docker-compose up -d",
    "cargo test --features foo",
    "cargo add serde --features derive",
    "pip install -r requirements.txt",
    "pip config set global.index-url x",
    "go test ./...",
    "go mod tidy",
    "go build -o x ./cmd/x",
    "go work sync",
    # --- valid second-level verbs must stay silent --------------------------
    # Adding chain validation is the point where a wrong verb list starts
    # accusing valid commands, so every documented verb of every declared
    # chain gets a case here.
    "docker container ls",
    "docker container ps",
    "docker container logs web",
    "docker image prune -f",
    "docker volume rm myvol",
    "docker network inspect bridge",
    "docker builder prune",
    "docker context use desktop-linux",
    "docker manifest inspect alpine",
    "docker plugin ls",
    "docker secret ls",
    "docker service ps web",
    "docker stack services mystack",
    "docker swarm join-token worker",
    "docker node ls",
    "docker trust sign x",
    "docker checkpoint ls",
    "docker compose config",
    "docker compose alpha viz",
    "docker compose watch",
    "docker-compose down -v",
    "git remote -v",
    "git remote set-url origin url",
    "git remote show origin",
    "git stash push -m wip",
    "git stash pop",
    "git stash list",
    "git stash apply stash@{0}",
    "git submodule update --init --recursive",
    "git submodule foreach 'git pull'",
    "git worktree add ../wt feature",
    "git bisect start",
    "git bisect good abc",
    "git notes show",
    # `git config` is deliberately not a chain: its second token is a key.
    "git config user.name x",
    "go mod download",
    "go mod why -m x",
    "go work use ./x",
    "go telemetry off",
    # `go tool` is deliberately not a chain: that slot names any tool binary.
    "go tool pprof x",
    "go env GOPATH",
    "pip cache dir",
    "pip index versions requests",
    "pip download -d x requests",
    # --- a hint must only fire in the slot where its target is valid --------
    # `lss -> ls` and `st -> set` are object verbs, not top-level commands, so
    # these fragment typos must stay quiet rather than suggest `docker ls`.
    "docker lss",
    "pip st requests",
]


@pytest.mark.parametrize("text", NO_FIX)
def test_valid_commands_left_alone(patched_client, text: str) -> None:
    assert get_corrections(text) == []


def test_forced_table_synthesises_missing_binary(patched_client) -> None:
    """A forced table must fix a bare fragment into a runnable command.

    `--manager git "comit -m x"` used to answer "No fix found" because the
    line had no `git` token to locate; it now prepends the binary.
    """
    from fixpm.rules import spec_for_binary

    spec = spec_for_binary("git")
    assert spec is not None
    corrections = get_corrections("comit -m x", spec=spec)
    assert [c.command for c in corrections] == ["git commit -m x"]


def test_forced_table_absent_binary_is_still_bounded(patched_client) -> None:
    """A valid fragment under a forced table stays silent."""
    from fixpm.rules import spec_for_binary

    spec = spec_for_binary("go")
    assert spec is not None
    assert get_corrections("mod tidy", spec=spec) == []


def test_max_three_suggestions(patched_client) -> None:
    corrections = get_corrections("npm isntall react")
    assert 1 <= len(corrections) <= 3


def test_scores_sorted_desc(patched_client) -> None:
    corrections = get_corrections("npm isntall react")
    scores = [c.score for c in corrections]
    assert scores == sorted(scores, reverse=True)
