from __future__ import annotations

import pytest

from fixpm.distance import edit_distance, rank, similarity


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("kitten", "sitting", 3),
        ("abc", "abc", 0),
        ("", "ab", 2),
        ("flaw", "lawn", 2),
        ("svae", "save", 1),   # OSA transposition costs 1, not 2
        ("isntall", "install", 1),
    ],
)


def test_edit_distance(a: str, b: str, expected: int) -> None:
    assert edit_distance(a, b) == expected


def test_similarity_bounds() -> None:
    assert similarity("npm", "npm") == 1.0
    assert similarity("", "") == 1.0
    assert similarity("abcd", "xyz") == pytest.approx(0.0)


def test_rank_orders_and_filters() -> None:
    ranked = rank("instal", ["uninstall", "install", "init"], min_score=0.5)
    assert ranked[0][0] == "install"
    assert all(score >= 0.5 for _, score in ranked)


def test_rank_caps_and_dedupes() -> None:
    ranked = rank("aaa", ["aaa", "aab", "aac", "aad"], top=2, min_score=0.5)
    assert len(ranked) == 2
    assert len({name for name, _ in ranked}) == 2
