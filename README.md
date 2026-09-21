# fixpm

[![CI](https://github.com/Max-code7997/fixpm/actions/workflows/ci.yml/badge.svg)](https://github.com/Max-code7997/fixpm/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fixpm.svg)](https://pypi.org/project/fixpm/)
[![Python versions](https://img.shields.io/pypi/pyversions/fixpm.svg)](https://pypi.org/project/fixpm/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Max-code7997/fixpm/blob/main/LICENSE)

**Interactive command fixer for mistyped CLIs — npm, git, docker, cargo, pip, go.**

You typed `npm isntall react`. Your terminal yelled at you. `fixpm` knows what you meant — pick the fix with arrow keys, press Enter, done.

<!-- Absolute URL on purpose: PyPI renders this long description outside the
     repository, so a relative path shows up there as a broken image. -->
![fixpm demo](https://raw.githubusercontent.com/Max-code7997/fixpm/main/docs/assets/demo.gif)

## Tested on

Manually verified end-to-end (hook install + detection + interactive fix) on:

- **Windows PowerShell** (native)
- **WSL2** (Ubuntu, bash hook)
- **Git Bash** on Windows (bash hook)

## Why

CLIs fail in very predictable ways: a mistyped subcommand (`isntall`, `comit`, `buid`), a missing flag prefix (`save-dev` instead of `--save-dev`), or a mistyped package name (`loadash`). Generic "did you mean" tools don't understand that `add` is valid for `yarn` but means `install` on `npm`, or that `--frozen-lockfile` belongs to `pnpm install`.

`fixpm` ships a declarative rule table per CLI plus live npm-registry lookups, so suggestions are syntax-aware, not just string-similar.

It runs **on the prompt path**, so it never re-executes your failed command to read its error output — it classifies from the command line alone. That is what keeps it under ~100 ms and free of side effects on a command that may not be idempotent. (Reading output by re-running is the usual approach in this space, and it costs the failed command's runtime a second time: a failing `npm` invocation measured 1.2–1.8 s here, before any suggestion appears.)

## Features

- **Automatic detection** — a tiny bash/zsh/PowerShell hook notices when a covered command exits non-zero and nudges you.
- **11 CLIs covered** — npm, npx, pnpx, pnpm, yarn, git, docker, docker-compose, cargo, pip and go.
- **Five error classes**: subcommand typo, flag typo, missing flag prefix (`--`), missing required argument, package-name typo.
- **Registry-backed package fixes** — candidates ranked by edit distance *and* weekly download count (typos like `loadash` → `lodash`, never a dead lookalike package).
- **Interactive or one-shot** — arrow-key selection, or `--dry-run` to print fixes.
- **Extensible rule tables** — adding a manager or command is editing a data table, not writing code.

## Install

**Recommended — from PyPI (all platforms):**

```bash
pipx install fixpm          # isolated CLI install
# or
pip install --user fixpm
```

**Standalone binaries (no Python needed):**

| Platform | One-line install |
| --- | --- |
| macOS / Linux | `curl -fsSL https://raw.githubusercontent.com/Max-code7997/fixpm/main/scripts/install.sh \| sh` |
| Windows (PowerShell) | `irm https://raw.githubusercontent.com/Max-code7997/fixpm/main/scripts/install.ps1 \| iex` |

Or download the single-file executable + sha256 directly from
[GitHub Releases](https://github.com/Max-code7997/fixpm/releases/latest).

**Package managers:**

```bash
# Homebrew (macOS / Linux) — prebuilt binary, no Python and no compile step.
# Installs both `fixpm` and `fixpm-probe` (the fast path the hook prefers).
brew tap Max-code7997/fixpm https://github.com/Max-code7997/homebrew-fixpm
brew install fixpm

# Scoop (Windows)
scoop bucket add fixpm https://github.com/Max-code7997/fixpm
scoop install fixpm
```

## Setup

Enable automatic failure detection (zsh):

```bash
echo 'eval "$(fixpm --init zsh)"' >> ~/.zshrc
```

or bash:

```bash
echo 'eval "$(fixpm --init bash)"' >> ~/.bashrc
```

or PowerShell (Windows):

```powershell
Add-Content $PROFILE 'fixpm --init powershell > $env:TEMP\fixpm-hook.ps1; . "$env:TEMP\fixpm-hook.ps1"'
```

No hook? Works manually too:

```bash
fixpm "npm isntall react"     # quote multi-token commands
```

## Demo

Text walkthrough of the interaction:

```console
$ npm isntall react --save-dev
npm ERR! Unknown command: "isntall"

  ↯ fix available — run fixpm        ← printed automatically by the hook

$ fixpm
? Apply a fix: (↑/↓ move · enter select · ctrl+c cancel)
❯ npm install react --save-dev   · command fix · 95%
  Skip — do nothing

→ npm install react --save-dev   ← executed after Enter
added 42 packages in 3s
```

A real-terminal recording of the PowerShell hook is embedded at the top of this README.

### What it catches

| You type | fixpm suggests | Class |
| --- | --- | --- |
| `npm isntall react` | `npm install react` | subcommand typo |
| `npm i loadash` | `npm i lodash` | package typo (registry-checked) |
| `npm install express save-dev` | `npm install express --save-dev` | missing flag prefix |
| `npm run` | `npm run <script>` | missing argument (not auto-executed) |
| `pnpm ad left-pad` | `pnpm add left-pad` | subcommand typo |
| `yarn globla add vite` | `yarn global add vite` | subcommand typo |
| `npx creat-react-app web` | `npx create-react-app web` | package typo |
| `git comit -m wip` | `git commit -m wip` | subcommand typo |
| `docker contaner ls` | `docker container ls` | subcommand typo |
| `docker container lss` | `docker container ls` | second-level verb typo |
| `go mod tidyy` | `go mod tidy` | second-level verb typo |
| `git remote ad origin url` | `git remote add origin url` | second-level verb typo |
| `docker-compose ud` | `docker-compose up` | subcommand typo |
| `cargo biuld --release` | `cargo build --release` | subcommand typo |
| `pip3 unistall requests` | `pip3 uninstall requests` | subcommand typo |
| `go tset ./...` | `go test ./...` | subcommand typo |

## How it works

1. The shell hook exports `$FIXPM_LAST_COMMAND` / `$FIXPM_LAST_EXIT_CODE`; `fixpm` reads them (or takes the command as arguments).
2. `detector.py` tokenizes the line, finds the CLI's binary, and classifies each issue against that CLI's rule table.
3. `corrector.py` turns issues into concrete commands; package typos go through `packages.py`, which queries the npm registry search API and ranks by `0.8 × edit-distance similarity + 0.2 × log(weekly downloads)` (clamped). Network failures degrade gracefully to a local corpus of popular packages plus a curated typo map — the tool never crashes offline.

## Fast probe (Go)

The hook runs the probe **on the prompt path**, so its start-up is a delay the
user feels after every failed command. Starting a Python interpreter plus
`typer` costs far more than the detection itself, so the probe path is also
available as a compiled Go binary:

```
fixpm (Python)       ~250 ms
fixpm-probe (Go)      ~95 ms
```

(Measured on Windows/Git Bash, 30 interleaved runs, median. A bare Go binary
needs ~75 ms just to start there, so almost all of the probe's cost is process
creation rather than detection.)

The shell hooks prefer `fixpm-probe` when it is on PATH and fall back to the
Python CLI otherwise. `fixpm doctor` reports which one is active.

It is published prebuilt, so you do not need a Go toolchain to get the fast
path: every release carries `fixpm-probe-<platform>-<arch>` (the same
`<platform>-<arch>` you find on the main binary), the Homebrew formula installs
it alongside `fixpm`, and `scripts/install.sh` fetches it when available.

```bash
# only needed if you want to build it yourself
cd go && go build -trimpath -ldflags="-s -w" -o ../fixpm-probe .
```

Rules are **not** duplicated: `scripts/gen_go_rules.py` generates
`go/rules_gen.go` straight from `src/fixpm/rules/*.py`, and
`scripts/gen_parity_vectors.py` records golden vectors from the real Python CLI
for `go test` to replay. Both have a `--check` mode for CI. Adding a rule in
Python is therefore enough; regenerate afterwards.

```bash
python scripts/gen_go_rules.py         # then: --check in CI
python scripts/gen_parity_vectors.py   # then: --check in CI
cd go && go test ./...
```

## Troubleshooting

**The hook never prints a hint after a failed npm command.**

1. Make sure the probe itself finds suggestions:
   ```bash
   fixpm --dry-run "npm isntall react"   # must exit 0 and print fixes
   ```
   If it prints `No fix found`, the typo simply isn't covered yet — the hook stays silent by design. PRs adding rules are welcome.
2. Make sure `fixpm` is actually on PATH *in that shell* (`command -v fixpm`). `pip install --user` puts it in Python's `Scripts` directory, which is often not on PATH — prefer `pipx`, or add the directory manually.
3. Still stuck? Re-run the failing command with `FIXPM_DEBUG=1` exported — the hook then shows why its probe failed instead of swallowing errors.

**Suspect you're running a stale copy?** (multiple installs can shadow each other on PATH) — run:

```bash
fixpm doctor
```

It prints the resolved binary, version, fast-probe status, rule-set fingerprint and per-shell hook status, and flags any other `fixpm` copies visible on PATH.

## Contributing

Contributions welcome — especially **rule tables** for more CLIs and deeper pnpm/yarn flag coverage.

```bash
git clone https://github.com/Max-code7997/fixpm && cd fixpm
pip install -e ".[dev]"
ruff check . && pytest
```

### Adding a rule

Rules are data, not code. To teach `fixpm` a new command, alias, flag, or common misspelling, edit the relevant table in `src/fixpm/rules/`:

```python
# src/fixpm/rules/npm.py
NPM = register(
    ManagerSpec(
        name="npm",
        binaries=("npm",),
        commands=("install", "run", "publish", ...),   # canonical top-level commands
        aliases={"i": "install", "innit": "init"},      # alt spelling -> canonical
        flags={"install": ("--save-dev", "-D", ...)},   # validated flags per command
        typo_hints={"isntall": "install"},              # deterministic overrides
    )
)
```

Guidelines:

- One PR per logical change (a new CLI, a batch of flags, …).
- Add a pytest case in `tests/test_corrections.py` for every new behavior — including a *negative* one when the change could cause a false suggestion.
- Flag lists may be partial — unknown flags on unlisted commands are simply not validated (conservative by design).
- Only declare `flags` for a command when the list is actually complete. An incomplete list makes `fixpm` call valid input wrong, which is worse than staying quiet; that is why the git/docker/cargo/pip/go tables leave `flags` empty.
- Set `subcommand_min_score` higher (0.7) for CLIs with a **plugin namespace** (`git lfs`, `docker buildx`, `cargo nextest`). At the npm-tuned 0.55 floor those valid commands score high enough to be misreported as typos (`nextest` → `test` is 0.571, `lfs` → `ls` is 0.667). Where a short typo then falls below the floor, add a `typo_hint` — hints bypass the distance check.
- Commands whose second word is a **verb** rather than user data belong in `chains` (`{"container": ("ls", "prune", …)}`), which is what validates the second slot. Leave out commands whose second token is a value — `git config <key>`, `go tool <name>`, `go env <VAR>` — since any list there would accuse valid input. A `typo_hint` is slot-checked, so `lss → ls` fires under `docker container` and nowhere else.
- Adding a spec needs no engine changes, but regenerate both artifacts so the Go probe stays in sync:

```bash
python scripts/gen_go_rules.py && python scripts/gen_parity_vectors.py
cd go && go test ./...
```

See [CONTRIBUTING notes above](#contributing); open an issue first for new package managers.

## Roadmap

- [x] Compiled Go probe for the hook path (see [Fast probe](#fast-probe-go))
- [x] Rule tables for git / docker / docker-compose / cargo / pip / go
- [x] Second-level verbs (`docker container ls`, `go mod tidy`, `pip cache purge`)
- [ ] Flag validation for non-npm CLIs, generated from each tool's own `--help`
- [ ] Deeper pnpm / yarn (Berry) flag coverage
- [x] PowerShell hook (`--init powershell`)
- [ ] fish hook
- [ ] Validate `npm run <script>` against local `package.json`
- [ ] On-disk registry cache with TTL
- [ ] `fixpm --explain` (why this suggestion)

## License

[MIT](LICENSE)
