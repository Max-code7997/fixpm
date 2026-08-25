from __future__ import annotations

import os

from typer.testing import CliRunner

from fixpm import __version__
from fixpm.cli import app

runner = CliRunner()


def test_doctor_reports_core_sections() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "command resolved" in result.output
    assert __version__ in result.output
    assert "fingerprint=" in result.output
    assert "hook bash" in result.output
    assert "hook ps cache" in result.output


def test_doctor_fingerprints_corpus() -> None:
    from fixpm.packages import POPULAR_PACKAGES

    result = runner.invoke(app, ["doctor"])
    assert f"corpus={len(POPULAR_PACKAGES)}" in result.output


def test_doctor_flags_shadow_copies(tmp_path, monkeypatch) -> None:
    fake_dir = tmp_path / "bin"
    fake_dir.mkdir()
    (fake_dir / "fixpm.exe").write_text("stub", encoding="utf-8")
    (fake_dir / "fixpm").write_text("stub", encoding="utf-8")
    monkeypatch.setenv("PATH", str(fake_dir) + os.pathsep + os.environ.get("PATH", ""))

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "other copies" in result.output
