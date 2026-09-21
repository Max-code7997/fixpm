"""cargo rule table — mistyped subcommand coverage.

``clippy`` and ``fmt`` are rustup components rather than cargo built-ins, but
they are near-universal in Rust projects and typos in them are common, so they
belong in the vocabulary. Subcommand slot only: no flag validation, no
``arg_required``, no registry lookups.
"""

from .base import ManagerSpec, register

CARGO = register(
    ManagerSpec(
        name="cargo",
        binaries=("cargo",),
        commands=(
            "add", "bench", "build", "check", "clean", "clippy", "doc", "fetch",
            "fix", "fmt", "generate-lockfile", "help", "init", "install",
            "locate-project", "login", "logout", "metadata", "new", "owner",
            "package", "pkgid", "publish", "read-manifest", "remove", "report",
            "rm", "run", "rustc", "rustdoc", "search", "test", "tree",
            "uninstall", "update", "vendor", "verify-project", "version", "yank",
        ),
        typo_hints={
            "buidl": "build", "bulid": "build", "biuld": "build",
            "tset": "test", "tets": "test",
            "isntall": "install", "instal": "install", "insall": "install",
            "unsintall": "uninstall", "uninstal": "uninstall",
            "pubish": "publish", "publsih": "publish",
            "chek": "check", "chekc": "check",
            "clena": "clean", "clern": "clean",
            "udpate": "update", "updte": "update",
            "nwe": "new",
            "vendro": "vendor", "vendr": "vendor",
            "remvoe": "remove", "remve": "remove",
            "bnech": "bench",
            "rnu": "run",
            "mteadata": "metadata", "metdata": "metadata",
            "fex": "fix",
            "yankk": "yank",
        },
        # cargo plugins live in the same subcommand slot (cargo nextest,
        # cargo watch, cargo audit), and `nextest` -> `test` scores 0.571.
        subcommand_min_score=0.7,
    )
)
