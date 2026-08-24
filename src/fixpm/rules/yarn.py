"""yarn (classic v1 + Berry basics) rule table — baseline coverage."""

from .base import ManagerSpec, register

YARN = register(
    ManagerSpec(
        name="yarn",
        binaries=("yarn", "yarnpkg"),
        commands=(
            "add", "install", "remove", "upgrade", "run", "link", "unlink",
            "list", "why", "bin", "config", "info", "publish", "pack", "cache",
            "audit", "outdated", "global", "create", "exec", "dlx", "set",
            "workspaces", "version", "versions", "licenses", "login", "logout",
            "tag", "team", "unplug", "dedupe", "constraints",
        ),
        aliases={"rm": "remove"},
        flags={
            "add": (
                "-D", "--dev", "-P", "--peer", "-O", "--optional", "-E", "--exact",
                "-T", "--tilde", "-g", "--global",
            ),
            "install": (
                "--production", "-P", "--frozen-lockfile", "--immutable",
                "--ignore-scripts", "--check-files",
            ),
            "remove": ("-D", "--dev", "-g", "--global"),
            "upgrade": ("-D", "--dev", "-g", "--global", "--latest"),
        },
        global_flags=(
            "-v", "--version", "-h", "--help", "--cwd", "--registry", "--verbose",
            "--json",
        ),
        value_flags=("--cwd", "--registry"),
        package_commands=("add", "dlx", "create", "global add"),
        arg_required=("run", "exec", "dlx", "add", "remove", "info", "why",
                      "config", "owner", "tag", "team"),
        sub_verbs=("add", "remove", "upgrade", "bin", "dir", "list", "ls",
                   "link", "unlink", "upgrade-interactive"),
        typo_hints={
            "instal": "install", "isntall": "install", "insall": "install",
            "remve": "remove",
            "uprade": "upgrade", "upgarde": "upgrade",
            "globla": "global",
            "exce": "exec",
            "lst": "list",
        },
    )
)
