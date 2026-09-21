"""docker + docker-compose rule tables — mistyped subcommand coverage.

Like ``git.py``: the subcommand slot and the second-level verb of chain
commands are validated, nothing else. No flag validation (docker's flag set is
per-subcommand and huge, and a stale entry would produce a false accusation),
no ``arg_required`` (``docker ps -a`` and ``docker system prune`` are valid with
no positional), no registry lookups.

``docker`` and ``docker-compose`` are separate specs on purpose: their command
sets barely overlap, so sharing one table would let ``docker-compose up`` be
validated against docker's vocabulary.
"""

from .base import ManagerSpec, register

DOCKER = register(
    ManagerSpec(
        name="docker",
        binaries=("docker",),
        commands=(
            "attach", "build", "builder", "buildx", "checkpoint", "commit",
            "compose",
            "config", "container", "context", "cp", "create", "diff", "events",
            "exec", "export", "history", "image", "images", "import", "info",
            "inspect", "kill", "load", "login", "logout", "logs", "manifest",
            "network", "node", "pause", "plugin", "port", "ps", "pull", "push",
            "rename", "restart", "rm", "rmi", "run", "save", "scan", "search",
            "secret", "service", "stack", "start", "stats", "stop", "swarm",
            "system", "tag", "top", "trust", "unpause", "update", "version",
            "volume", "wait",
        ),
        typo_hints={
            "buid": "build", "bulid": "build", "biuld": "build",
            "runn": "run",
            # verb-slot hints (the target is a docker object verb, not a
            # top-level command, so they never apply in the other slot)
            "ud": "up", "lss": "ls",
            "pss": "ps",
            "puhs": "push", "psuh": "push",
            "pul": "pull", "pll": "pull",
            "exce": "exec", "exex": "exec",
            "inspec": "inspect", "inpsect": "inspect", "ispect": "inspect",
            "imags": "images", "imgaes": "images", "imges": "images",
            "iamge": "image", "imge": "image",
            "compse": "compose", "comopse": "compose", "compsoe": "compose",
            "contaner": "container", "conatiner": "container",
            "contianer": "container",
            "volum": "volume", "volme": "volume", "vloume": "volume",
            "netwrok": "network", "netowrk": "network", "newtork": "network",
            "systm": "system", "sytem": "system",
            "strat": "start", "sart": "start",
            "stp": "stop", "sotp": "stop",
            "restrat": "restart", "restar": "restart", "restat": "restart",
            "logni": "login", "loign": "login",
            "logut": "logout", "loguot": "logout",
            "serch": "search", "seach": "search", "searc": "search",
            "tga": "tag", "tgas": "tag",
            "verison": "version", "vresion": "version",
            "updte": "update", "upadte": "update",
            "comit": "commit", "commti": "commit",
            "atach": "attach", "attch": "attach",
            "creat": "create", "cerate": "create",
            "kil": "kill",
            "puse": "pause", "pusae": "pause",
            "histroy": "history", "hsitory": "history",
            "improt": "import", "ipmort": "import",
            "exprot": "export", "exoprt": "export",
            "plugni": "plugin", "plguin": "plugin",
            "turst": "trust", "trsut": "trust",
            "swam": "swarm", "swrm": "swarm",
            "servce": "service", "servie": "service",
            "stak": "stack", "stck": "stack",
            "secert": "secret", "secrect": "secret",
            "ndoe": "node",
            "manifset": "manifest", "manifst": "manifest",
            "contex": "context", "contxt": "context",
            "checkpiont": "checkpoint",
        },
        # Second-level verbs. `docker <object> <verb>` is a closed vocabulary
        # per object (`docker container ls`, `docker volume prune`), so this
        # slot can be validated — a typo in it is otherwise invisible, since
        # the object itself is a known command. Keep each list complete: the
        # floor below only catches near-misses, so an unlisted-but-valid verb
        # stays quiet anyway.
        chains={
            "builder": ("build", "ls", "prune"),
            "checkpoint": ("create", "ls", "rm"),
            "container": (
                "attach", "commit", "cp", "create", "diff", "exec", "export",
                "inspect", "kill", "logs", "ls", "pause", "port", "prune",
                "rename", "restart", "rm", "run", "start", "stats", "stop",
                "top", "unpause", "update", "wait",
            ),
            # The compose plugin is a separate binary with its own verb set
            # (see docker-compose above); list it again so `docker compose
            # <verb>` gets the same treatment as the standalone CLI.
            "compose": (
                "alpha", "attach", "bridge", "build", "commit", "config",
                "cp", "create", "down", "events", "exec", "export", "help",
                "images", "kill", "logs", "ls", "pause", "port", "ps",
                "publish", "pull", "push", "restart", "rm", "run", "scale",
                "start", "stats", "stop", "top", "unpause", "up", "version",
                "wait", "watch",
            ),
            "context": ("create", "export", "import", "inspect", "ls", "rm",
                        "show", "update", "use"),
            "image": ("build", "history", "import", "inspect", "load", "ls",
                      "prune", "pull", "push", "rm", "save", "tag"),
            "manifest": ("annotate", "create", "inspect", "push", "rm"),
            "network": ("connect", "create", "disconnect", "inspect", "ls",
                        "prune", "rm"),
            "node": ("demote", "inspect", "ls", "promote", "ps", "rm",
                     "update"),
            "plugin": ("create", "disable", "enable", "inspect", "install",
                       "ls", "rm", "set", "upgrade"),
            "secret": ("create", "inspect", "ls", "rm"),
            "service": ("create", "inspect", "logs", "ls", "ps", "rm",
                        "rollback", "scale", "update"),
            "stack": ("config", "deploy", "ls", "ps", "rm", "services"),
            "swarm": ("ca", "init", "join", "join-token", "leave", "unlock",
                      "unlock-key", "update"),
            "system": ("df", "events", "info", "prune"),
            "trust": ("inspect", "key", "revoke", "sign", "signer"),
            "volume": ("create", "inspect", "ls", "prune", "rm"),
        },
        # docker plugins (buildx, compose) and CLI plugins in general are a
        # namespace we cannot enumerate, so demand a close match.
        subcommand_min_score=0.7,
    )
)

DOCKER_COMPOSE = register(
    ManagerSpec(
        name="docker-compose",
        binaries=("docker-compose",),
        commands=(
            "build", "config", "cp", "create", "down", "events", "exec",
            "help", "images", "kill", "logs", "ls", "pause", "port", "ps",
            "publish", "pull", "push", "restart", "rm", "run", "scale", "start",
            "stop", "top", "unpause", "up", "version", "watch",
        ),
        typo_hints={
            "ud": "up", "pu": "up", "upp": "up",
            "dwon": "down", "donw": "down",
            "buid": "build", "bulid": "build", "biuld": "build",
            "restar": "restart", "restrat": "restart",
            "strat": "start", "stp": "stop", "sotp": "stop",
            "log": "logs", "lgs": "logs",
            "psl": "ps", "pss": "ps",
            "confg": "config", "cofnig": "config",
            "scle": "scale", "scael": "scale",
            "versoin": "version", "verison": "version",
            "exce": "exec", "pul": "pull", "puhs": "push",
        },
        subcommand_min_score=0.7,
    )
)
