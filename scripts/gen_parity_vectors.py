"""Generate the golden parity vectors for the Go probe.

The Python implementation is the reference. This script runs it over a corpus
of failed commands and records the exact stdout and exit code, so the Go port
can be checked byte-for-byte in `go test`

Every vector is guaranteed network-free: the reference run uses a registry stub
that raises if a lookup would ever reach npm. Vectors that need the registry
would be non-deterministic and are rejected outright.

    python scripts/gen_parity_vectors.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fixpm.corrector import get_corrections  # noqa: E402
from fixpm.packages import (  # noqa: E402
    POPULAR_FALLBACK,
    Suggestion,
    base_name,
)
from fixpm.rules import spec_for_binary  # noqa: E402

TARGET = ROOT / "go" / "testdata" / "parity.json"

# Commands chosen to exercise every branch of the detector: each manager, every
# issue kind, alias resolution, the `yarn global <verb>` chain, value-flags,
# `--` passthrough, quoting, and the negative cases that must stay silent.
#
# Package tokens must be curated typos (keys of POPULAR_FALLBACK): a real
# package name such as `react` would send the reference run to the npm registry
# to confirm it exists, which the _NoNetwork stub rejects as non-deterministic.
COMMANDS: list[tuple[str, str | None]] = [
    # --- subcommand typos, one per manager -------------------------------
    ("npm isntall react", None),
    ("npm instal react", None),
    ("npm unistall react", None),
    ("npm updte react", None),
    ("pnpm isntall react", None),
    ("pnpm remve react", None),
    ("yarn globla add vite", None),
    ("yarn instal", None),
    ("npm run-scirpt build", None),
    ("npm xyzzy react", None),
    # --- valid aliases must produce nothing ------------------------------
    ("npm ci", None),
    ("npm t", None),
    ("npm list", None),
    # --- flag typos ------------------------------------------------------
    ("npm install loadash --save-devv", None),
    ("npm install loadash --sav-dev", None),
    ("npm --prefx ./x install react", None),
    ("npm install --frozen-lockfile", None),
    ("pnpm install --frozen-lockfil", None),
    # --- missing dashes --------------------------------------------------
    ("npm install exprses save-dev", None),
    ("npm install exprses save", None),
    ("npm uninstall save-dev", None),
    ("yarn add reat dev", None),
    # --- missing argument ------------------------------------------------
    ("npm run", None),
    ("npm exec", None),
    ("npm config", None),
    ("pnpm run", None),
    ("pnpm dlx", None),
    ("yarn add", None),
    ("yarn why", None),
    ("npm uninstall", None),
    # --- package-first (npx / pnpx) --------------------------------------
    ("npx", None),
    ("npx loadash web", None),
    ("npx --package foo loadash", None),
    ("pnpx", None),
    ("npx loadash", None),
    # --- package typos: curated only, so no registry access --------------
    ("npm i loadash", None),
    ("npm install axois", None),
    ("npm install reat", None),
    ("pnpm add loadash", None),
    ("yarn add reat", None),
    ("npm uninstall mongose", None),
    ("npm i reat", None),
    ("npm install loadash@^4", None),
    ("npx loadash@4 -y", None),
    # --- yarn global chain ----------------------------------------------
    ("yarn global add reat", None),
    ("yarn global ad reat", None),
    ("yarn global remov reat", None),
    # --- value flags consume the next token ------------------------------
    ("npm --prefix ./x isntall react", None),
    ("npm install --registry https://r.example loadash", None),
    ("npm -w packages/app loadash", None),
    # --- passthrough separator exempts everything after ------------------
    ("npm install loadash -- --save-dev", None),
    ("npm run build -- --frozen-lockfile", None),
    # --- quoting / shlex edge cases --------------------------------------
    ('npm install "loadash@^4"', None),
    ("npm install 'a b'", None),
    ("npm isntall \"react\" --save-dev", None),
    ("npm install loadash --prefix '/my dir'", None),
    ('npm isntall react "unclosed', None),
    # --- negative cases: nothing to fix ---------------------------------
    ("ls -la", None),
    ("git status", None),
    ("", None),
    ("   ", None),
    # --- forced manager --------------------------------------------------
    # Bare fragments (no binary token): the detector synthesises the binary so
    # the suggestion is runnable. Package tokens must stay inside the curated
    # typo map, or the reference run would need the npm registry.
    ("isntall loadash", "npm"),
    ("isntall loadash", "pnpm"),
    ("i loadash", "npm"),
    ("isntall loadash", "yarn"),
    ("comit -m x", "git"),
    ("tset", "go"),
    ("mod tidy", "go"),
    # --- non-npm CLIs: subcommand typo ----------------------------------
    ("git comit -m x", None),
    ("git chekcout main", None),
    ("git stauts", None),
    ("git mrege main", None),
    ("git puhs origin main", None),
    ("git revparse HEAD", None),
    ("docker contaner ls", None),
    ("docker buid -t x .", None),
    ("docker resta rt abc", None),
    ("docker-compose ud", None),
    ("docker-compose dwon", None),
    ("cargo biuld --release", None),
    ("cargo tset", None),
    ("pip instal requests", None),
    ("pip3 unistall requests", None),
    ("go tset ./...", None),
    ("go biuld", None),
    # --- second-level verbs (chain commands) ------------------------------
    ("docker container lss", None),
    ("docker image pruen", None),
    ("docker system prun", None),
    ("docker compose ud", None),
    ("docker compose dwon", None),
    ("git remote ad origin url", None),
    ("git stash aplpy", None),
    ("git submodule updte", None),
    ("go mod tidyy", None),
    ("go work sycn", None),
    ("pip cache purg", None),
    ("pip config st global.index-url x", None),
    # --- valid second-level verbs stay silent ----------------------------
    ("docker container ls", None),
    ("docker image prune -f", None),
    ("docker compose config", None),
    ("git remote set-url origin url", None),
    ("git stash push -m wip", None),
    ("git submodule update --init --recursive", None),
    ("go mod download", None),
    ("go mod why -m x", None),
    ("go work use ./x", None),
    ("pip cache dir", None),
    # A hint whose target is not valid in the command slot must not leak:
    ("docker lss", None),
    # --- the per-spec similarity floor: unlisted-but-valid stays silent --
    ("git lfs pull", None),
    ("git flow init", None),
    ("cargo nextest run", None),
    ("cargo watch -x test", None),
    # --- valid flags/args on the new CLIs must not be second-guessed -----
    ("git commit -m x", None),
    ("git add -A", None),
    ("git -c core.pager=cat log", None),
    ("docker run -it --rm ubuntu bash", None),
    ("docker compose up -d", None),
    ("docker system prune -af", None),
    ("docker-compose up -d", None),
    ("cargo test --features foo", None),
    ("pip install -r requirements.txt", None),
    ("go test ./...", None),
    ("go mod tidy", None),
]


class _NoNetwork:
    """Registry stub that can only answer from the curated typo map.

    Any vector that would need a real npm lookup raises instead of silently
    depending on the network.
    """

    def suggest(self, name: str, limit: int = 3) -> list[Suggestion]:
        target = base_name(name).lower()
        curated = POPULAR_FALLBACK.get(target)
        if curated is None:
            raise AssertionError(
                f"vector needs the npm registry for {name!r}; "
                "use a curated typo or drop the vector"
            )
        return [Suggestion(curated, 0, 0.95)]


def assert_network_free(text: str, manager: str | None) -> None:
    """Fail loudly if this vector would need a real npm lookup.

    Runs the reference logic in-process against a stub that raises on any
    registry access, so non-deterministic vectors can never be recorded.
    """
    spec = spec_for_binary(manager) if manager else None
    if manager and spec is None:
        raise AssertionError(f"unknown manager {manager!r}")
    stripped = text.strip()
    if stripped:
        get_corrections(stripped, spec=spec, client=_NoNetwork())


def capture(text: str, manager: str | None) -> tuple[int, str]:
    """Run the real Python CLI and capture its stdout bytes.

    Capturing the actual process rather than rebuilding the string keeps this
    honest: it records what the tool really emits (including platform newline
    translation) instead of what we believe it emits.
    """
    args = [sys.executable, "-m", "fixpm"]
    if manager:
        args += ["--manager", manager]
    args += ["--dry-run", text]

    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(args, cwd=str(ROOT), env=env,
                          capture_output=True)
    stdout = proc.stdout.decode("utf-8")
    # Python's text-mode stdout translates "\n" to os.linesep on Windows. The
    # probe emits LF everywhere on purpose, so record the normalised form and
    # let TestLineEndingsAreLF document the difference explicitly.
    return proc.returncode, stdout.replace("\r\n", "\n")


def render() -> str:
    vectors = []
    for text, manager in COMMANDS:
        assert_network_free(text, manager)
        args = (["--manager", manager] if manager else []) + ["--dry-run", text]
        code, out = capture(text, manager)
        vectors.append({"args": args, "exit": code, "stdout": out})

    payload = {
        "comment": (
            "Generated by scripts/gen_parity_vectors.py from the Python "
            "implementation. Do not edit by hand."
        ),
        "vectors": vectors,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the file is out of date")
    args = parser.parse_args()

    content = render()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != content:
            print(f"{TARGET} is stale; run scripts/gen_parity_vectors.py",
                  file=sys.stderr)
            return 1
        print(f"{TARGET} is up to date")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET} ({len(COMMANDS)} vectors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
