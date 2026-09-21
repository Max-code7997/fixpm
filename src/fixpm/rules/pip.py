"""pip rule table — mistyped subcommand coverage.

`pip` and `pip3` share one table. Subcommand slot only: no flag validation
(pip's install flags alone are dozens and version-dependent), no
``arg_required``, no registry lookups — ``pip install <name>`` is not checked
against PyPI, which keeps the probe offline and fast.
"""

from .base import ManagerSpec, register

PIP = register(
    ManagerSpec(
        name="pip",
        binaries=("pip", "pip3"),
        commands=(
            "cache", "check", "completion", "config", "debug", "download",
            "freeze", "hash", "help", "index", "inspect", "install", "list",
            "lock", "search", "show", "uninstall", "wheel",
        ),
        typo_hints={
            "isntall": "install", "instal": "install", "intsall": "install",
            "insall": "install", "intall": "install",
            "unistall": "uninstall", "uninstal": "uninstall",
            "unintall": "uninstall",
            "frezze": "freeze", "freez": "freeze",
            "shwo": "show", "sho": "show",
            "serch": "search", "seach": "search",
            "lis": "list", "lst": "list",
            "chek": "check", "chekc": "check",
            "whel": "wheel", "weel": "wheel",
            "dowload": "download", "donwload": "download",
            "confg": "config", "cofnig": "config",
            "cahe": "cache",
            "hahs": "hash",
            "inspec": "inspect", "ispect": "inspect",
            "completin": "completion",
            "deug": "debug",
            # verb-slot hint: `set` is not a top-level pip command, so this can
            # only fire inside `pip config <verb>`.
            "st": "set",
        },
        # `pip cache purge`, `pip config set`, `pip index versions` — small
        # closed verb sets, so the second slot can be validated.
        chains={
            "cache": ("dir", "info", "list", "purge", "remove", "wheel"),
            "config": ("debug", "describe", "edit", "get", "list", "set",
                       "unset"),
            "index": ("versions",),
        },
        subcommand_min_score=0.7,
    )
)
