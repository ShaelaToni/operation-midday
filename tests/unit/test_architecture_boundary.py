"""Clean-architecture boundary guard.

Asserts that no module under domain/ or application/ imports Django or the
infrastructure app 'noon'. The pure core must stay framework-free so its
tests run without a database and the architecture cannot silently rot.
"""
import ast
import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
PURE_PACKAGES = ["domain", "application"]
FORBIDDEN_ROOTS = {"django", "noon"}


def _pure_module_paths():
    paths = []
    for package in PURE_PACKAGES:
        pkg_dir = PROJECT_ROOT / package
        if pkg_dir.exists():
            paths.extend(sorted(pkg_dir.rglob("*.py")))
    return paths


def _imported_roots(source: str):
    """Return the set of top-level module names imported by the source."""
    roots = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # Ignore relative imports (node.level > 0); they stay within the package.
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("module_path", _pure_module_paths(), ids=lambda p: str(p.relative_to(PROJECT_ROOT)))
def test_pure_module_has_no_forbidden_imports(module_path):
    source = module_path.read_text()
    violations = _imported_roots(source) & FORBIDDEN_ROOTS
    assert not violations, (
        f"{module_path.relative_to(PROJECT_ROOT)} imports forbidden module(s): "
        f"{sorted(violations)}. domain/ and application/ must stay framework-free."
    )
