"""Shared fixtures: a deterministic fake registry client."""

from __future__ import annotations

import pytest

from fixpm.packages import Suggestion


class FakeRegistry:
    """Maps known names to their intended fix; returns [] otherwise."""

    def __init__(self, mapping: dict[str, str] | None = None):
        self.mapping = mapping or {}

    def suggest(self, name: str, limit: int = 3) -> list[Suggestion]:
        fix = self.mapping.get(name.lower())
        if fix is None or fix.lower() == name.lower():
            return []
        return [Suggestion(fix, weekly_downloads=100_000, score=0.97)]


@pytest.fixture
def fake_registry() -> FakeRegistry:
    return FakeRegistry(
        {
            "loadash": "lodash",
            "creat-react-app": "create-react-app",
            "lodass": "lodash",
        }
    )


@pytest.fixture
def patched_client(fake_registry: FakeRegistry, monkeypatch: pytest.MonkeyPatch):
    import fixpm.corrector as corrector_module

    monkeypatch.setattr(corrector_module, "_default_client", lambda: fake_registry)
    return fake_registry
