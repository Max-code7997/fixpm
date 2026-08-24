"""npm rule table — the most complete coverage; keep it that way.

To extend: append canonical commands to ``commands``, alternate spellings to
``aliases``, validated flags to ``flags[<command>]``, and curated misspellings
to ``typo_hints``. Every value in ``aliases``/``typo_hints`` must exist in the
vocabulary (``commands`` ∪ ``aliases.keys()``).
"""

from .base import ManagerSpec, register

NPM = register(
    ManagerSpec(
        name="npm",
        binaries=("npm",),
        commands=(
            "help", "access", "adduser", "audit", "bin", "bugs", "cache", "ci",
            "completion", "config", "dedupe", "deprecate", "diff", "dist-tag",
            "docs", "doctor", "edit", "exec", "explain", "explore",
            "find-dupes", "fund", "help-search", "hook", "init", "install",
            "link", "ll", "login", "logout", "ls", "org", "outdated", "owner",
            "pack", "ping", "pkg", "prefix", "profile", "prune", "publish",
            "rebuild", "repo", "restart", "root", "run", "sbom", "search",
            "set", "shrinkwrap", "star", "stars", "start", "stop", "team",
            "test", "token", "uninstall", "unpublish", "unstar", "update",
            "version", "view", "whoami",
        ),
        aliases={
            "i": "install",
            "add": "install",
            "create": "init",
            "un": "uninstall",
            "remove": "uninstall",
            "rm": "uninstall",
            "up": "update",
            "run-script": "run",
            "t": "test",
            "tst": "test",
            "list": "ls",
            "ln": "link",
            "c": "config",
            "dist-tags": "dist-tag",
        },
        flags={
            "install": (
                "--save", "-S", "--save-dev", "-D", "--save-optional", "-O",
                "--save-exact", "-E", "--save-peer", "--save-bundle",
                "--no-save", "--dry-run", "--global", "-g", "--production",
                "--omit", "--legacy-peer-deps", "--strict-peer-deps", "--force",
                "--offline", "--prefer-offline", "--audit", "--no-audit",
                "--fund", "--no-fund", "--workspaces", "-w", "-ws", "--workspace",
            ),
            "uninstall": (
                "--save", "-S", "--save-dev", "-D", "--save-optional", "-O",
                "--global", "-g", "--no-save", "--workspaces", "-w", "--workspace",
            ),
            "update": (
                "--global", "-g", "--json", "--save", "-S", "--save-dev", "-D",
                "--workspaces", "-w", "--workspace",
            ),
            "outdated": ("--global", "-g", "--json", "--long", "--workspaces", "-w"),
            "run": ("--if-present", "--silent", "--workspace", "-w", "--workspaces"),
            "exec": (
                "--package", "-p", "--call", "-c", "--yes", "-y",
                "--workspace", "-w",
            ),
            "init": ("--yes", "-y", "--scope", "--workspaces", "-w", "--workspace"),
        },
        global_flags=(
            "-v", "--version", "-h", "--help", "--prefix", "--registry",
            "--loglevel", "--silent", "-s", "--json", "--color", "--no-color",
            "--verbose", "--userconfig", "--location", "--omit",
        ),
        value_flags=("--prefix", "--registry", "--loglevel", "--userconfig",
                     "--location", "--omit", "-w", "--workspace"),
        package_commands=("install", "add", "init"),
        arg_required=("run", "exec", "config", "uninstall", "cache", "pkg",
                      "org", "team", "access", "dist-tag", "token", "profile",
                      "set"),
        typo_hints={
            "isntall": "install", "instal": "install", "insatll": "install",
            "instll": "install", "intsall": "install", "istall": "install",
            "innit": "init",
            "unistall": "uninstall", "uninsatll": "uninstall",
            "uninstal": "uninstall",
            "updte": "update", "upadte": "update", "uodate": "update",
            "pubish": "publish", "pulbish": "publish",
            "serach": "search", "saerch": "search",
            "lnk": "link",
            "lst": "list",
            "run-scirpt": "run-script", "runscirpt": "run-script",
            "exuect": "exec", "exeute": "exec",
            "verison": "version", "vresion": "version",
            "audti": "audit", "cach": "cache", "outdatd": "outdated",
            "rebulid": "rebuild", "logut": "logout", "logni": "login",
        },
    )
)
