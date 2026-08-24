"""npm registry client with graceful offline degradation.

Uses stdlib urllib (zero dependencies). Every network error is swallowed and
degrades to a small curated typo map, so the CLI never crashes without a
connection.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from . import __version__
from .distance import similarity

SEARCH_URL = "https://registry.npmjs.org/-/v1/search"
DOWNLOAD_URL = "https://api.npmjs.org/downloads/point/last-week/{pkg}"
USER_AGENT = f"fixpm/{__version__} (https://github.com/fixpm/fixpm)"

# Curated high-signal typos so the tool stays useful fully offline.
POPULAR_FALLBACK: dict[str, str] = {
    "loadash": "lodash", "lodass": "lodash", "lodahs": "lodash",
    "expresss": "express", "exprses": "express", "epxress": "express",
    "reactt": "react", "reat": "react", "raect": "react",
    "vuee": "vue", "vu": "vue",
    "angualr": "angular",
    "axioss": "axios", "axois": "axios",
    "momentt": "moment",
    "typsecript": "typescript", "typescirpt": "typescript",
    "eslit": "eslint", "esint": "eslint", "eslintt": "eslint",
    "jestt": "jest",
    "nodemonn": "nodemon",
    "mongose": "mongoose", "mongoos": "mongoose",
    "sequilize": "sequelize",
    "dotnev": "dotenv",
    "tailwindcsss": "tailwindcss",
    "graphl": "graphql",
    "prettie": "prettier",
}

# Local corpus of popular package names. The npm search API has poor recall
# for misspelled queries (searching "loadash" never surfaces "lodash"), so a
# local pool gives transposition-style typos something to fuzzy-match against,
# fully offline. Contributors: append well-known names freely.
POPULAR_PACKAGES: tuple[str, ...] = (
    "react", "react-dom", "react-router", "vue", "vue-router", "pinia",
    "angular", "svelte", "next", "nuxt", "astro", "remix", "gatsby",
    "express", "koa", "fastify", "hapi", "nest", "socket.io", "ws",
    "lodash", "underscore", "ramda", "axios", "superagent", "ky", "got",
    "moment", "dayjs", "date-fns", "luxon",
    "typescript", "eslint", "prettier", "biome", "jest", "vitest", "mocha",
    "chai", "sinon", "playwright", "cypress",
    "vite", "webpack", "rollup", "esbuild", "parcel", "swc", "turbo",
    "tailwindcss", "bootstrap", "bulma", "sass", "less", "postcss",
    "styled-components", "emotion", "framer-motion",
    "three", "d3", "chart.js", "jquery", "gsap",
    "redux", "zustand", "jotai", "immer", "rxjs",
    "zod", "yup", "joi", "ajv", "class-validator",
    "mongoose", "prisma", "sequelize", "typeorm", "knex", "redis",
    "graphql", "trpc", "urql",
    "nodemon", "concurrently", "pm2",
    "dotenv", "cross-env", "commander", "yargs", "inquirer", "prompts",
    "chalk", "kleur", "picocolors", "ora",
    "debug", "winston", "pino", "loglevel",
    "uuid", "nanoid",
    "js-yaml", "yaml", "fs-extra", "glob", "rimraf", "mkdirp",
    "semver", "minimist",
    "jsonwebtoken", "bcrypt", "passport", "helmet", "cors", "multer",
    "body-parser", "compression", "morgan", "cookie-parser", "http-proxy",
)

# Popularity prior for corpus-only hits whose live download count is unknown.
CORPUS_POP_PRIOR = 0.5

@dataclass(frozen=True)
class Suggestion:
    name: str
    weekly_downloads: int  # 0 when unknown
    score: float


def base_name(spec: str) -> str:
    """Strip a trailing version specifier: ``lodash@^4`` -> ``lodash``,
    ``@scope/pkg@1.2`` -> ``@scope/pkg``. A bare scope prefix is kept."""
    head, _, _tail = spec.rpartition("@")
    # head == '' means the only @ was the leading scope marker — nothing to strip
    return head if head else spec


def format_downloads(n: int | None) -> str:
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


class NpmRegistry:
    """Search-backed suggester. Score = 0.62 * similarity + 0.38 * popularity."""

    def __init__(self, timeout: float = 2.5):
        self.timeout = timeout
        self._cache: dict[str, object] = {}
        self._offline = False  # circuit breaker after repeated failures

    # -- network -----------------------------------------------------------

    def _get_json(self, url: str) -> object | None:
        if self._offline:
            return None
        if url in self._cache:
            return self._cache[url]
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
            ValueError,
        ):
            if len(self._cache) == 0:
                self._offline = True  # nothing ever succeeded; stop trying
            return None
        if len(self._cache) > 256:
            self._cache.clear()
        self._cache[url] = data
        return data

    def search(self, name: str, size: int = 8) -> list[str]:
        url = f"{SEARCH_URL}?{urlencode({'text': name, 'size': size})}"
        data = self._get_json(url)
        objects = data.get("objects", []) if isinstance(data, dict) else []
        names = []
        for obj in objects:
            pkg = obj.get("package", {})
            if isinstance(pkg.get("name"), str):
                names.append(pkg["name"])
        return names

    def weekly_downloads(self, names: list[str]) -> dict[str, int | None]:
        out: dict[str, int | None] = {}
        for name in names:
            url = DOWNLOAD_URL.format(pkg=quote(name, safe="@"))
            data = self._get_json(url)
            value = data.get("downloads") if isinstance(data, dict) else None
            out[name] = value if isinstance(value, int) else None
        return out

    # -- public API --------------------------------------------------------

    def suggest(self, name: str, limit: int = 3) -> list[Suggestion]:
        target = base_name(name).lower()
        # Curated map wins first: npm search has poor recall for misspelled
        # queries (searching "loadash" never surfaces "lodash"), so classic
        # typos must not depend on the network at all.
        curated = POPULAR_FALLBACK.get(target)
        if curated is not None:
            return [Suggestion(curated, 0, 0.95)]

        registry_names = self.search(target)[:5]
        if any(n.lower() == target for n in registry_names):
            return []  # exact hit: the name was fine, a rename can't be the fix
        downloads = self.weekly_downloads(registry_names)
        # Merge in close corpus matches; they keep the tool useful offline and
        # cover typo shapes the search API cannot recall.
        corpus_hits = [
            p for p in POPULAR_PACKAGES
            if similarity(target, p.lower()) >= 0.5
        ][:3]

        scored: list[Suggestion] = []
        seen: set[str] = set()
        entries = [(n, False) for n in registry_names] \
            + [(p, True) for p in corpus_hits]
        for cand, from_corpus in entries:
            low = cand.lower()
            if low == target or low in seen:
                continue  # exact match means the name was fine; no rename fix
            seen.add(low)
            sim = similarity(target, low)
            if sim < 0.4:
                continue
            dl = downloads.get(cand)
            if dl is not None:
                pop = min(1.0, math.log1p(dl) / math.log1p(3_000_000))
            else:
                dl = 0
                pop = CORPUS_POP_PRIOR if from_corpus else 0.0
            suggestion = Suggestion(cand, dl, round(0.62 * sim + 0.38 * pop, 3))
            if suggestion.score >= 0.4:
                scored.append(suggestion)
        scored.sort(key=lambda s: (-s.score, s.name))
        return scored[:limit]
