"""Bundled rule tables. Importing a module here registers its spec."""

from . import cargo, docker, git, go, npm, npx, pip, pnpm, yarn  # noqa: F401
from .base import ManagerSpec, all_specs, register, spec_for_binary

__all__ = ["ManagerSpec", "all_specs", "register", "spec_for_binary"]
