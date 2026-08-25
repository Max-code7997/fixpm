#!/usr/bin/env sh
# fixpm installer for macOS / Linux.
#
# One-line install:
#   curl -fsSL https://raw.githubusercontent.com/Max-code7997/fixpm/main/scripts/install.sh | sh
#
# Overrides (testing / mirrors):
#   FIXPM_RELEASE_BASE          download base URL (default: latest GitHub release)
#   FIXPM_INSTALL_DIR           target directory   (default: ~/.local/bin)
#   FIXPM_SKIP_VERSION_CHECK=1  don't execute the binary after install
set -eu

REPO="Max-code7997/fixpm"
BASE="${FIXPM_RELEASE_BASE:-https://github.com/$REPO/releases/latest/download}"
DEST="${FIXPM_INSTALL_DIR:-$HOME/.local/bin}"

case "$(uname -s)" in
    Linux)  platform="linux" ;;
    Darwin) platform="macos" ;;
    *) echo "error: unsupported platform '$(uname -s)'. On Windows use install.ps1." >&2; exit 1 ;;
esac
case "$(uname -m)" in
    x86_64|amd64)   arch="x64" ;;
    arm64|aarch64)  arch="arm64" ;;
    *) echo "error: unsupported architecture '$(uname -m)'" >&2; exit 1 ;;
esac
ASSET="fixpm-${platform}-${arch}"

fetch() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --retry 3 -o "$2" "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$2" "$1"
    else
        echo "error: need curl or wget to download" >&2
        exit 1
    fi
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "downloading $ASSET from $BASE ..."
fetch "$BASE/$ASSET" "$TMP/$ASSET"
fetch "$BASE/$ASSET.sha256" "$TMP/$ASSET.sha256"

expected=$(cut -d' ' -f1 "$TMP/$ASSET.sha256" | tr -d "[:space:]")
if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$TMP/$ASSET" | cut -d' ' -f1)
elif command -v shasum >/dev/null 2>&1; then
    actual=$(shasum -a 256 "$TMP/$ASSET" | cut -d' ' -f1)
else
    echo "error: no sha256sum/shasum available for checksum verification" >&2
    exit 1
fi
if [ "$expected" != "$actual" ]; then
    echo "error: sha256 mismatch for $ASSET" >&2
    echo "  expected: $expected" >&2
    echo "  actual:   $actual" >&2
    exit 1
fi
echo "checksum ok"

mkdir -p "$DEST"
cp "$TMP/$ASSET" "$DEST/fixpm"
chmod 0755 "$DEST/fixpm"
echo "installed: $DEST/fixpm"

case ":$PATH:" in
    *":$DEST:"*) ;;
    *) echo "note: $DEST is not on your PATH."
       echo "      add it:  export PATH=\"$DEST:\$PATH\"  (put this line in ~/.bashrc or ~/.zshrc)" ;;
esac

if [ "${FIXPM_SKIP_VERSION_CHECK:-0}" = "1" ]; then
    echo "(version check skipped)"
else
    "$DEST/fixpm" --version
fi
