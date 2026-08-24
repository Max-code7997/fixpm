"""npx / pnpx rule tables — package-first CLIs: the first positional IS a
package name, so typo handling routes through the registry lookup."""

from .base import ManagerSpec, register

NPX = register(
    ManagerSpec(
        name="npx",
        binaries=("npx",),
        package_first=True,
        global_flags=(
            "-v", "--version", "-h", "--help", "-p", "--package", "-c", "--call",
            "-y", "--yes", "-q", "--quiet", "--registry", "--prefer-offline",
            "--offline",
        ),
        value_flags=("-p", "--package", "--registry"),
    )
)

PNPX = register(
    ManagerSpec(
        name="pnpx",
        binaries=("pnpx",),
        package_first=True,
        global_flags=("-v", "--version", "-h", "--help", "-p", "--package",
                      "-y", "--yes", "--registry"),
        value_flags=("-p", "--package", "--registry"),
    )
)
