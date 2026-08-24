"""CLI entry point.

Modes:
  fixpm                       fix $FIXPM_LAST_COMMAND (set by shell hook)
  fixpm <command words...>    fix an explicit command line
  fixpm --dry-run <cmd>       print fixes without prompting/executing
  fixpm --init zsh|bash       emit the hook script for eval "$(...)"
"""

from __future__ import annotations

import os
import subprocess
import sys
from importlib import resources

import typer

from . import __version__
from .corrector import get_corrections
from .interactive import choose
from .rules import all_specs, spec_for_binary
from .rules.base import KIND_LABEL

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Fix broken npm / npx / pnpm / yarn commands.",
)

ENV_COMMAND = "FIXPM_LAST_COMMAND"
ENV_EXIT_CODE = "FIXPM_LAST_EXIT_CODE"

_HOOKS = {"bash": "fixpm.bash", "zsh": "fixpm.zsh"}


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
        help='Emit a hook script for the given shell ("bash" or "zsh"). '
             'Use inside eval: eval "$(fixpm --init zsh)".',
    ),
) -> None:
    if init_shell is not None:
        _emit_hook(init_shell)
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

    choice = choose(corrections)
    if choice is None:
        typer.echo("Cancelled.")
        raise typer.Exit(code=1)

    typer.secho(f"-> {choice.command}", fg="cyan", bold=True)
    if not choice.executable:
        typer.echo("This fix needs manual arguments — copy it and fill them in.")
        raise typer.Exit(code=0)

    raise typer.Exit(code=subprocess.run(choice.command, shell=True).returncode)


def _emit_hook(shell: str) -> None:
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
    rc_file = "~/.zshrc" if shell == "zsh" else "~/.bashrc"
    typer.secho(f"# Add this line to your {rc_file}: "
                f'eval "$(fixpm --init {shell})"', dim=True, err=True)


if __name__ == "__main__":
    app()
