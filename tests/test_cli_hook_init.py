from __future__ import annotations

from typer.testing import CliRunner

from fixpm.cli import _RC_HINTS, app

runner = CliRunner()


def test_rc_hints_cover_all_shells() -> None:
    assert set(_RC_HINTS) == {"bash", "zsh", "powershell"}
    for _rc, enable_line in _RC_HINTS.values():
        assert "fixpm --init" in enable_line


def test_init_powershell_emits_hook() -> None:
    result = runner.invoke(app, ["--init", "powershell"])
    assert result.exit_code == 0
    assert "__Fixpm-Hook" in result.output
    assert "global:prompt" in result.output
    # stderr hint is suppressed when stdout is not a tty (e.g. profile eval)
    assert "Add this line" not in result.output


def test_init_bash_still_works() -> None:
    result = runner.invoke(app, ["--init", "bash"])
    assert result.exit_code == 0
    assert "__fixpm_arm" in result.output


def test_init_zsh_still_works() -> None:
    result = runner.invoke(app, ["--init", "zsh"])
    assert result.exit_code == 0
    assert "__fixpm_precmd" in result.output


def test_init_unsupported_shell_fails() -> None:
    result = runner.invoke(app, ["--init", "fish"])
    assert result.exit_code == 1
    assert "Unsupported shell" in result.output
