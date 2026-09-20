"""CLI entry point.

Modes:
  fixpm                       fix $FIXPM_LAST_COMMAND (set by shell hook)
  fixpm <command words...>    fix an explicit command line
  fixpm --dry-run <cmd>       print fixes without prompting/executing
  fixpm --init zsh|bash|powershell   emit the hook script
"""

from __future__ import annotations

import os
import subprocess
import sys

import typer

from . import __version__
from .corrector import get_corrections
from .rules import all_specs, spec_for_binary
from .rules.base import KIND_LABEL

# NOTE: `fixpm.interactive` (-> questionary -> prompt_toolkit, ~280 ms) and
# `importlib.resources` (~74 ms) are imported lazily at their call sites. The
# shell hook runs `fixpm --dry-run` after every failed npm-family command, so
# startup latency is user-visible and only the interactive / --init paths
# actually need those modules.

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Fix broken npm / npx / pnpm / yarn commands.",
)

ENV_COMMAND = "FIXPM_LAST_COMMAND"
ENV_EXIT_CODE = "FIXPM_LAST_EXIT_CODE"

_HOOKS = {"bash": "fixpm.bash", "zsh": "fixpm.zsh", "powershell": "fixpm.ps1"}

# Per-shell rc file and the exact line users should add to it.
_RC_HINTS = {
    "bash": ("~/.bashrc", 'eval "$(fixpm --init bash)"'),
    "zsh": ("~/.zshrc", 'eval "$(fixpm --init zsh)"'),
    # PowerShell cannot eval multi-line output from a subexpression, so the
    # hook is written to a temp file and dot-sourced from disk.
    "powershell": (
        "$PROFILE",
        'fixpm --init powershell > $env:TEMP\\fixpm-hook.ps1; '
        '. "$env:TEMP\\fixpm-hook.ps1"',
    ),
}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"fixpm {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    command: list[str] | None = typer.Argument(
        None, help="Failed command to fix. Reads $FIXPM_LAST_COMMAND when omitted."
    ),
    manager: str | None = typer.Option(
        None, "--manager", "-m",
        help="Force a package manager instead of auto-detecting.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print fixes without prompting or executing."
    ),
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
    init_shell: str | None = typer.Option(
        None, "--init",
        help='Emit a hook script for the given shell ("bash", "zsh" or '
             '"powershell"). Use inside eval: eval "$(fixpm --init zsh)".',
    ),
) -> None:
    if init_shell is not None:
        _emit_hook(init_shell)
        return
    if command == ["doctor"]:
        # The variadic argument would otherwise swallow the subcommand
        # (same click quirk that forced --init to be a flag).
        doctor()
        return
    if ctx.invoked_subcommand is not None:
        return

    text = " ".join(command).strip() if command \
        else os.environ.get(ENV_COMMAND, "").strip()
    if not text:
        typer.secho("No command provided.", fg="red")
        typer.echo(
            'Run `fixpm <failed command>` or install a shell hook first: '
            '`fixpm --init zsh`.'
        )
        raise typer.Exit(code=1)

    spec = None
    if manager:
        spec = spec_for_binary(manager)
        if spec is None:
            names = ", ".join(sorted({s.binaries[0] for s in all_specs()}))
            raise typer.BadParameter(f"unknown manager {manager!r}; pick one of: {names}")

    corrections = get_corrections(text, spec=spec)
    if not corrections:
        typer.secho(f"No fix found for: {text}", fg="yellow")
        raise typer.Exit(code=1)

    if dry_run:
        for c in corrections:
            typer.echo(f"  [{KIND_LABEL[c.kind]}] {c.command}")
        return

    # ~280 ms of questionary/prompt_toolkit, paid only when we actually prompt.
    from .interactive import choose

    choice = choose(corrections)
    if choice is None:
        typer.echo("Cancelled.")
        raise typer.Exit(code=1)

    typer.secho(f"-> {choice.command}", fg="cyan", bold=True)
    if not choice.executable:
        typer.echo("This fix needs manual arguments — copy it and fill them in.")
        raise typer.Exit(code=0)

    raise typer.Exit(code=subprocess.run(choice.command, shell=True).returncode)


@app.command()
def doctor() -> None:
    """Show which fixpm binary, rule set and hooks are active.

    Triage for "my fixpm behaves like an old version" — usually a stale
    copy shadowing the real one on PATH.
    """
    import hashlib
    import shutil
    from datetime import datetime
    from pathlib import Path

    exe = shutil.which("fixpm")
    typer.echo(f"command resolved : {exe or 'NOT FOUND ON PATH'}")
    typer.echo(f"version          : {__version__}")
    typer.echo(f"package dir      : {Path(__file__).resolve().parent}")

    # The shell hook prefers the compiled probe because it runs on the prompt
    # path; without it every failed npm command pays Python's start-up.
    probe = shutil.which("fixpm-probe")
    typer.echo(
        "fast probe       : "
        + (f"{probe}  (hook uses this path)" if probe else
           "not installed  (hook falls back to this Python CLI)")
    )

    from . import packages as _pkg
    from . import rules as _rules  # noqa: E402

    # Fingerprint the rule tables themselves, not just the package corpus:
    # `doctor` is the tool for "why does my fixpm not know this rule yet?", so
    # a rules edit must change the value it prints.
    rule_files = sorted(Path(_rules.__file__).parent.glob("*.py"))
    rule_blob = b"\n".join(f.read_bytes() for f in rule_files)
    corpus_blob = "\n".join(_pkg.POPULAR_PACKAGES).encode("utf-8")
    fingerprint = hashlib.sha1(rule_blob + b"\n" + corpus_blob).hexdigest()[:8]
    rules_mtime = datetime.fromtimestamp(
        max(f.stat().st_mtime for f in rule_files)
    ).strftime("%Y-%m-%d %H:%M")
    typer.echo(
        f"rule set         : {len(rule_files)} rule modules, "
        f"corpus={len(_pkg.POPULAR_PACKAGES)} pkgs, "
        f"curated={len(_pkg.POPULAR_FALLBACK)} typos, "
        f"fingerprint={fingerprint}, mtime={rules_mtime}"
    )

    home = Path.home()
    hook_checks = [
        ("bash", home / ".bashrc", "fixpm --init bash"),
        ("zsh", home / ".zshrc", "fixpm --init zsh"),
    ]
    for docs in (home / "Documents", home / "OneDrive" / "Documents"):
        for sub in ("WindowsPowerShell", "PowerShell"):
            hook_checks.append((
                "powershell",
                docs / sub / "Microsoft.PowerShell_profile.ps1",
                "fixpm --init powershell",
            ))
    seen: set[Path] = set()
    for shell, path, needle in hook_checks:
        if path in seen:
            continue
        seen.add(path)
        installed = False
        if path.exists():
            installed = needle in path.read_text(encoding="utf-8", errors="ignore")
        state = "installed" if installed else "not installed"
        typer.echo(f"hook {shell:<11}: {state}  ({path})")
    cache = Path(os.environ.get("TEMP", str(home / ".tmp"))) / "fixpm-hook.ps1"
    typer.echo(f"hook ps cache    : "
               f"{'present' if cache.exists() else 'absent'}  ({cache})")

    exe_resolved = Path(exe).resolve() if exe else None
    shadows: list[str] = []
    seen_dirs: set[Path] = set()
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        d = Path(entry)
        if d in seen_dirs:
            continue
        seen_dirs.add(d)
        for name in ("fixpm.exe", "fixpm.cmd", "fixpm"):
            candidate = d / name
            if candidate.exists():
                resolved = candidate.resolve()
                if exe_resolved is None or resolved != exe_resolved:
                    shadows.append(str(resolved))
    if shadows:
        typer.echo("other copies     : " + ", ".join(shadows))
        typer.echo("                   PATH order decides which one runs; "
                   "remove or rebuild stale copies.")


def _emit_hook(shell: str) -> None:
    from importlib import resources

    filename = _HOOKS.get(shell)
    if filename is None:
        supported = ", ".join(sorted(_HOOKS))
        typer.secho(f"Unsupported shell {shell!r}. Supported: {supported}",
                    fg="red", err=True)
        raise typer.Exit(code=1)
    script = (resources.files("fixpm.shell") / filename).read_text(encoding="utf-8")
    # Write LF-only bytes directly: Windows pipes translate "\n" to "\r\n",
    # and a unix shell sourcing CRLF text ends up with broken hook definitions
    # (functions named "...{\r"). Git Bash/MSYS silently tolerates CRLF, WSL
    # and native Linux do not — so the raw byte stream must be LF.
    sys.stdout.buffer.write(script.replace("\r\n", "\n").encode("utf-8"))
    sys.stdout.buffer.flush()
    if sys.stdout.isatty():
        # Interactive use: remind the user how to enable it. When the output
        # is captured by eval/$(...) the hint would be startup noise.
        rc_file, enable_line = _RC_HINTS[shell]
        typer.secho(f"# Add this line to your {rc_file}: {enable_line}",
                    dim=True, err=True)


if __name__ == "__main__":
    app()
