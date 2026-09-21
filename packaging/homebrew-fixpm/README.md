# homebrew-fixpm

Homebrew tap for [fixpm](https://github.com/Max-code7997/fixpm) — interactive fixer for mistyped CLI commands: npm, git, docker, cargo, pip and go.

## Install (users)

```bash
brew tap Max-code7997/fixpm https://github.com/Max-code7997/homebrew-fixpm
brew install fixpm
```

or in one line:

```bash
brew install Max-code7997/fixpm/fixpm
```

## Maintainers

### Repository setup

1. Create a new GitHub repo named `homebrew-fixpm` under `Max-code7997` (public, empty).
2. Copy this folder's contents as the repo root, so the layout is:

   ```
   homebrew-fixpm/
   └── Formula/
       └── fixpm.rb
   ```

3. Commit and push.

### Testing a formula change

Homebrew does not run on Windows — verify on a Mac, or spin up a one-off macOS
GitHub runner (see below).

```bash
brew install --build-from-source ./Formula/fixpm.rb   # install from the local formula
fixpm --version && fixpm --dry-run "npm isntall react"
brew audit --strict ./Formula/fixpm.rb                # style/lint checks
brew uninstall fixpm
```

One-off verification on a GitHub macOS runner (no Mac needed): create a
disposable workflow on any repo of yours:

```yaml
jobs:
  formula-test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - run: brew install --build-from-source ./Formula/fixpm.rb
      - run: |
          fixpm --version
          fixpm --dry-run "npm isntall react"
```

### Updating after a new fixpm release

The formula pins the PyPI **sdist** URL + sha256 for fixpm and every runtime
dependency. After publishing a new version to PyPI:

1. Resolve the dependency closure and fetch fresh url/sha256 pairs:

   ```bash
   pip install --dry-run --quiet --ignore-installed --report report.json fixpm==<NEW_VERSION>
   ```

   (`--ignore-installed` is essential — otherwise pip skips already-installed
   deps and the closure comes back incomplete.)

2. Update `Formula/fixpm.rb`:
   - fixpm's own `url` / `sha256`
   - any dependency whose version changed (their `resource` url/sha256);
     add/remove `resource` blocks if the dependency set changed
3. Sanity-check every changed pair by downloading the sdist and comparing:

   ```bash
   curl -fsSL -o /tmp/x.tar.gz "<url>" && shasum -a 256 /tmp/x.tar.gz
   ```

4. Run the test commands above, commit, push to `homebrew-fixpm`.

(An automation script for steps 1–2 is planned; until then this is manual.)
