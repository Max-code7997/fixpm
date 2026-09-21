"""git rule table — unknown/mistyped subcommand coverage.

Scope is deliberately narrow: only the *subcommand slot* is validated. ``flags``
stays empty so the engine skips flag validation entirely, because git's valid
flags differ per subcommand and change between releases — an incomplete list
would make fixpm tell you a perfectly valid flag is wrong, which is worse than
staying quiet. Same reasoning for ``arg_required``: ``git add -A`` and
``git commit -m x`` legitimately have no positional argument.

``package_commands`` is empty too, which keeps this table off the npm registry
(no network, and no "check package name" guesses for branch names).

``chains`` covers the commands whose second word is a verb rather than a user
value. ``git config`` is the counter-example and stays out: its second token is
a config key, so treating it as a verb slot would second-guess valid input.
"""

from .base import ManagerSpec, register

GIT = register(
    ManagerSpec(
        name="git",
        binaries=("git",),
        commands=(
            # --- porcelain --------------------------------------------------
            "add", "am", "archive", "bisect", "blame", "branch", "bundle",
            "checkout", "cherry-pick", "citool", "clean", "clone", "commit",
            "config", "describe", "diff", "fetch", "format-patch", "gc",
            "grep", "gui", "init", "log", "maintenance", "merge", "mergetool",
            "mv", "notes", "pull", "push", "range-diff", "rebase", "reset",
            "restore", "revert", "rm", "shortlog", "show", "show-branch",
            "sparse-checkout", "stash", "status", "submodule", "switch", "tag",
            "whatchanged", "worktree",
            # --- ancillary --------------------------------------------------
            "annotate", "bugreport", "daemon", "difftool", "filter-branch",
            "instaweb", "quiltimport", "request-pull", "send-email",
            # --- plugin subcommands that are widely installed ----------------
            # Listed so a valid-but-unlisted command is never called a typo.
            # Staying silent is an acceptable failure; a false accusation is not.
            "lfs", "flow", "subtree",
            # --- plumbing (surfaces in scripts and CI a lot) ----------------
            "cat-file", "check-attr", "check-ignore", "check-mailmap",
            "check-ref-format", "checkout-index", "commit-graph",
            "commit-tree", "count-objects", "credential", "credential-cache",
            "credential-store", "diff-files", "diff-index", "diff-tree",
            "fast-export", "fast-import", "fetch-pack", "for-each-ref",
            "fsck", "get-tar-commit-id", "hash-object", "index-pack",
            "ls-files", "ls-remote", "ls-tree", "mailinfo", "mailsplit",
            "merge-base", "merge-file", "merge-index", "merge-tree", "mktag",
            "mktree", "multi-pack-index", "name-rev", "pack-objects",
            "pack-redundant", "pack-refs", "patch-id", "prune",
            "prune-packed", "read-tree", "receive-pack", "reflog", "refs",
            "remote", "repack", "replace", "rev-list", "rev-parse",
            "send-pack", "show-index", "show-ref", "stripspace",
            "symbolic-ref", "unpack-file", "unpack-objects", "update-index",
            "update-ref", "upload-archive", "upload-pack", "var",
            "verify-commit", "verify-pack", "verify-tag", "write-tree",
            # --- help itself -------------------------------------------------
            "help", "version",
        ),
        aliases={"stage": "add"},
        typo_hints={
            "comit": "commit", "commti": "commit", "ommit": "commit",
            "cmomit": "commit",
            "chekcout": "checkout", "checout": "checkout", "checkou": "checkout",
            "checkot": "checkout", "chckout": "checkout",
            "stauts": "status", "statis": "status", "sattus": "status",
            "statu": "status",
            "brnach": "branch", "branhc": "branch", "brach": "branch",
            "mrege": "merge", "mege": "merge", "merg": "merge",
            "rebaes": "rebase", "rebse": "rebase",
            "stahs": "stash", "stsh": "stash", "stah": "stash",
            "dff": "diff", "dif": "diff",
            "cloen": "clone", "clon": "clone", "clne": "clone",
            "initt": "init", "inti": "init",
            "tgas": "tag", "tga": "tag",
            "pul": "pull", "puul": "pull", "pulll": "pull",
            "puhs": "push", "psuh": "push",
            "fetech": "fetch", "fetc": "fetch",
            "remtoe": "remote", "remte": "remote",
            "resrt": "reset", "restroe": "restore", "restor": "restore",
            "shwo": "show", "shw": "show",
            "clea": "clean", "clena": "clean",
            "submodle": "submodule", "submoduel": "submodule",
            "swtich": "switch", "swich": "switch", "swtch": "switch",
            "bisct": "bisect", "biset": "bisect",
            "revparse": "rev-parse", "revpars": "rev-parse",
            # verb-slot hints: both targets are also valid top-level commands,
            # so these work in either slot (`git ad .` -> `git add .`).
            "ad": "add", "pup": "pop",
        },
        # Verbs of the commands that take one. These sets are closed and
        # documented, so a typo is worth reporting; a command whose second
        # token is user data (config, tag, branch, ...) is left out entirely.
        chains={
            "bisect": ("bad", "good", "help", "log", "new", "old", "replay",
                       "reset", "run", "skip", "start", "terms", "visualize"),
            "notes": ("add", "append", "copy", "edit", "get-ref", "list",
                      "merge", "prune", "remove", "show"),
            "remote": ("add", "get-url", "prune", "remove", "rename", "rm",
                       "set-branches", "set-head", "set-url", "show",
                       "update"),
            "stash": ("apply", "branch", "clear", "create", "drop", "export",
                      "import", "list", "pop", "push", "save", "show",
                      "store"),
            "submodule": ("absorbgitdirs", "add", "deinit", "foreach", "init",
                          "set-branch", "set-url", "status", "summary", "sync",
                          "update"),
            "worktree": ("add", "list", "lock", "move", "prune", "remove",
                         "repair", "unlock"),
        },
        # git has a plugin namespace (git-lfs, git-flow, ...), so an unknown
        # token is only called a typo when it is a very close match.
        subcommand_min_score=0.7,
    )
)
