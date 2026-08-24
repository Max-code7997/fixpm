"""String-similarity primitives.

We use optimal-string-alignment (a restricted Damerau-Levenshtein) so common
transpositions ("svae" -> "save") cost 1, not 2. Pure stdlib, zero deps.
"""

from __future__ import annotations


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return la + lb
    prev2: list[int] | None = None
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if (
                prev2 is not None
                and i > 1
                and j > 1
                and ca == b[j - 2]
                and a[i - 2] == b[j - 1]
            ):
                v = min(v, prev2[j - 2] + 1)
            cur[j] = v
        prev2, prev = prev, cur
    return prev[lb]


def similarity(a: str, b: str) -> float:
    """Normalized similarity in [0, 1]; 1 means identical."""
    m = max(len(a), len(b))
    if m == 0:
        return 1.0
    return 1.0 - edit_distance(a, b) / m


def rank(
    target: str,
    candidates: list[str],
    *,
    top: int = 3,
    min_score: float = 0.6,
) -> list[tuple[str, float]]:
    """Best matches for *target*, sorted by score desc then length/name asc."""
    seen: set[str] = set()
    scored: list[tuple[str, float]] = []
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        s = similarity(target, c)
        if s >= min_score:
            scored.append((c, s))
    scored.sort(key=lambda t: (-t[1], len(t[0]), t[0]))
    return scored[:top]
