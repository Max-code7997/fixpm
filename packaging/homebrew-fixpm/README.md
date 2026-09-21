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

Homebrew does not run on Windows, so this repository's CI job
**Homebrew formula (macOS)** is the verification: it installs the formula from
the commit under test, then asserts that both binaries report the expected
version and each fixes a typo. A green job is the only evidence that the
formula works — treat a red one as a broken release, not as CI noise.

To do it by hand on a Mac:

```bash
brew install --formula ./Formula/fixpm.rb
fixpm --version && fixpm-probe --version
fixpm --dry-run "npm isntall react"
brew audit --strict ./Formula/fixpm.rb
brew uninstall fixpm
```

### Updating after a new fixpm release

The formula installs prebuilt binaries, so there is no Python dependency
closure to resolve — four url/sha256 pairs, taken straight from the release:

```bash
TAG=vX.Y.Z
for a in fixpm-macos-arm64 fixpm-probe-macos-arm64 \
         fixpm-linux-x64 fixpm-probe-linux-x64; do
    printf '%s ' "$a"
    curl -fsSL "https://github.com/Max-code7997/fixpm/releases/download/$TAG/$a.sha256"
done
```

1. Set `version` to the tag, and update the four `url` + `sha256` pairs (the
   two `on_arm`/`on_intel` blocks, plus the same two inside `resource "probe"`).
2. Keep this directory and `Max-code7997/homebrew-fixpm` byte-identical — the
   tap is what users install, this copy is what CI verifies.
3. Push both. The CI job **Homebrew formula (macOS)** does a real install
   against the published assets, so a broken pin fails there instead of on a
   user's machine.
