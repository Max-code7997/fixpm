"""go toolchain rule table — mistyped subcommand coverage.

Subcommand slot only: no flag validation (``go build``/``go test`` pass flags
straight through to the compiler and the test binary, so an allow-list would be
wrong most of the time), no ``arg_required``, no registry lookups.

Second-level verbs (``go mod tidy``, ``go work sync``) are validated through
``chains``; ``go tool`` is deliberately absent from it, because that slot names
an arbitrary tool binary (``go tool pprof``, plus any ``go-<name>`` on PATH).
"""

from .base import ManagerSpec, register

GO = register(
    ManagerSpec(
        name="go",
        binaries=("go",),
        commands=(
            "bug", "build", "clean", "doc", "env", "fix", "fmt", "generate",
            "get", "help", "install", "list", "mod", "run", "telemetry", "test",
            "tool", "version", "vet", "work",
        ),
        typo_hints={
            "buid": "build", "bulid": "build", "biuld": "build",
            "tset": "test", "tets": "test",
            "isntall": "install", "instal": "install",
            "clena": "clean", "clea": "clean",
            "genrate": "generate", "generat": "generate",
            "rnu": "run",
            "lst": "list",
            "tols": "tool",
            "verison": "version", "versoin": "version",
            "vte": "vet", "vett": "vet",
            "dco": "doc", "dc": "doc",
            "ebg": "bug",
            "hlep": "help",
            "telemetery": "telemetry",
            "envv": "env",
            "feix": "fix",
        },
        chains={
            "mod": ("download", "edit", "graph", "init", "tidy", "vendor",
                    "verify", "why"),
            "telemetry": ("local", "off", "on", "upload"),
            "work": ("edit", "init", "sync", "use", "vendor"),
        },
        # `go` dispatches to external tools too (go tool, plus any `go-<name>`
        # binary on PATH), so keep the same conservative floor as git/docker.
        subcommand_min_score=0.7,
    )
)
