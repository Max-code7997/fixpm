"""Registry client behavior: weighting, exact-match skip, offline fallback."""

from __future__ import annotations

import pytest

from fixpm.packages import (
    NpmRegistry,
    base_name,
    format_downloads,
)


class StubRegistry(NpmRegistry):
    """Serves canned JSON without touching the network."""

    def __init__(self, search_names: list[str], downloads: dict[str, int]):
        super().__init__()
        self.search_names = search_names
        self.downloads = downloads

    def _get_json(self, url: str):  # type: ignore[override]
        if "/-/v1/search" in url:
            return {"objects": [{"package": {"name": n}} for n in self.search_names]}
        name = url.rsplit("/", 1)[-1]
        return {"downloads": self.downloads.get(name, 0)}


class OfflineRegistry(NpmRegistry):
    def _get_json(self, url: str):  # type: ignore[override]
        return None


def test_base_name_strips_versions() -> None:
    assert base_name("lodash@^4") == "lodash"
    assert base_name("@scope/pkg@1.2.3") == "@scope/pkg"
    assert base_name("@scope/pkg") == "@scope/pkg"
    assert base_name("react") == "react"


def test_popularity_beats_marginal_similarity() -> None:
    stub = StubRegistry(
        search_names=["reactx-pro", "react"],
        downloads={"react": 40_000_000, "reactx-pro": 300},
    )
    suggestions = stub.suggest("reactx")
    assert suggestions, "expected at least one suggestion"
    assert suggestions[0].name == "react"
    assert all(0 <= s.score <= 1 for s in suggestions)


def test_exact_match_yields_no_rename() -> None:
    stub = StubRegistry(search_names=["react"], downloads={"react": 1})
    assert stub.suggest("react") == []


def test_corpus_catches_typos_the_search_api_misses() -> None:
    # Regression: "npm i loadahs" must suggest lodash via the local corpus,
    # because npm search cannot recall lodash from misspelled queries.
    stub = StubRegistry(search_names=["loadahs-core"], downloads={})
    names = [s.name for s in stub.suggest("loadahs")]
    assert "lodash" in names


def test_offline_falls_back_to_curated_map() -> None:
    suggestions = OfflineRegistry().suggest("loadash")
    assert [s.name for s in suggestions] == ["lodash"]


def test_curated_map_wins_even_when_online() -> None:
    # npm search has poor recall for misspellings; the curated map must take
    # priority over whatever fuzzy junk the search API returns.
    stub = StubRegistry(
        search_names=["sloadash", "loadashes6"], downloads={"sloadash": 5}
    )
    assert [s.name for s in stub.suggest("loadash")] == ["lodash"]


def test_offline_unknown_package_is_empty() -> None:
    assert OfflineRegistry().suggest("zzz-not-a-real-pkg") == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, "?"), (0, "0"), (999, "999"), (1500, "2k"),
     (2_500_000, "2.5M"), (45_000_000, "45.0M")],
)
def test_format_downloads(value: int | None, expected: str) -> None:
    assert format_downloads(value) == expected
