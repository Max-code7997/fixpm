"""Bundled rule tables. Importing a module here registers its manager spec."""

from . import npm, npx, pnpm, yarn  # noqa: F401
from .base import ManagerSpec, all_specs, register, spec_for_binary

__all__ = ["ManagerSpec", "all_specs", "register", "spec_for_binary"]
