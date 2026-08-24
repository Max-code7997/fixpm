"""pnpm rule table — baseline coverage, iterate toward npm parity."""

from .base import ManagerSpec, register

PNPM = register(
    ManagerSpec(
        name="pnpm",
        binaries=("pnpm",),
        commands=(
            "add", "install", "update", "remove", "unlink", "link", "list",
            "why", "run", "test", "exec", "create", "dlx", "start", "restart",
            "store", "rebuild", "outdated", "pack", "publish", "init",
            "import", "licenses", "audit", "setup", "env", "patch", "bin",
            "root", "help", "completion",
        ),
        aliases={
            "i": "install",
            "rm": "remove",
            "un": "remove",
            "up": "update",
            "ls": "list",
            "r": "run",
            "t": "test",
            "ln": "link",
        },
        flags={
            "add": (
                "-D", "--save-dev", "-P", "--save-prod", "-O", "--save-optional",
                "--save-peer", "-E", "--save-exact", "-g", "--global",
                "--workspace", "-w",
            ),
            "install": (
                "--frozen-lockfile", "--prod", "-P", "--dev", "-D", "--offline",
                "--prefer-offline", "--ignore-scripts", "--lockfile-only",
            ),
            "remove": ("-D", "--save-dev", "-g", "--global", "--workspace", "-w"),
            "run": ("--parallel", "--recursive", "-r", "--filter", "--if-present",
                    "--workspace", "-w"),
            "dlx": (),
        },
        global_flags=(
            "-v", "--version", "-h", "--help", "--registry", "--filter",
            "--reporter", "--json",
        ),
        value_flags=("--registry", "--filter", "-w", "--workspace-dir"),
        package_commands=("add", "dlx", "install", "create", "remove"),
        arg_required=("run", "exec", "dlx", "test", "create", "why", "patch",
                      "env", "store"),
        typo_hints={
            "isntall": "install", "instal": "install", "insall": "install",
            "upadte": "update", "uodate": "update",
            "remve": "remove", "reomve": "remove",
            "addd": "add",
            "exuect": "exec",
            "whyy": "why",
        },
    )
)
