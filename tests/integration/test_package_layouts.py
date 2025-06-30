import subprocess
from pathlib import Path

import pytest

from ..utils.package_utils import create_package_structure
from ..utils.venv_utils import create_virtual_env, run_in_venv, setup_test_env
from ..utils.verification_utils import verify_installation


@pytest.mark.parametrize("pip_arguments", [("--no-build-isolation",), ("-e",)])
def test_src_layout_installation(tmp_path, pip_arguments):
    """Test installation of a package using src layout."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    venv_dir = create_virtual_env(tmp_path / "venv")
    setup_test_env(venv_dir, backend_dir)

    package_dir = tmp_path / "test-package"
    package_dir.mkdir()

    # Create directory structure
    package_tree = {
        "mypackage": {
            "core": {
                "base.pyx": """
def get_value():
    return 42
""",
            },
            "utils": {
                "helpers.py": """
def helper_func():
    return "helper"
""",
            }
        }
    }
    create_package_structure(package_dir / "src", package_tree)

    # Create pyproject.toml with only modern configuration
    with open(package_dir / "pyproject.toml", "w") as f:
        f.write(f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "test-package"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]
include = ["mypackage*"]

[tool.hwh.cython]
language = "c"
""")

    # Create test script
    test_script = package_dir / "test_import.py"
    test_script.write_text("""
from mypackage.core.base import get_value
from mypackage.utils.helpers import helper_func

assert get_value() == 42
assert helper_func() == "helper"
print("Import test passed!")
""")

    try:
        # Install package
        arguments = ["pip", "install", *pip_arguments, str(package_dir)]
        run_in_venv(
            venv_dir,
            arguments,
            show_output=True,
        )

        # Verify installation
        verify_installation(venv_dir, test_script, "Import test passed!")

    except subprocess.CalledProcessError as e:
        print("\nTest failed")
        print("Output:", e.output)
        print("Error:", e.stderr)
        raise


@pytest.mark.parametrize("pip_arguments", [("--no-build-isolation",), ("-e",)])
def test_src_layout_mixed_modules(tmp_path, pip_arguments):
    """Test src layout with mixed Python and Cython modules."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    # Create test environment
    venv_dir = create_virtual_env(tmp_path / "venv")
    setup_test_env(venv_dir, backend_dir)

    # TODO: fix the package creation functions and refactor this PoS
    # Create package structure
    package_dir = tmp_path / "mixed-package"
    package_dir.mkdir()

    src_dir = package_dir / "src"
    src_dir.mkdir()
    pkg_dir = src_dir / "mixedpkg"
    pkg_dir.mkdir()

    # Create top level init an import
    (pkg_dir / "__init__.py").write_text("""
from .core import fast_core_func
from .utils import slow_util_func

__all__ = ['fast_core_func', 'slow_util_func']
""")

    # Cython module
    (pkg_dir / "core.pyx").write_text("""
def fast_core_func():
    cdef int i, total = 0
    for i in range(1000):
        total += i
    return total
""")

    # Python module
    (pkg_dir / "utils.py").write_text("""
def slow_util_func():
    total = 0
    for i in range(1000):
        total += i
    return total
""")

    # pyproject.toml
    with open(package_dir / "pyproject.toml", "w") as f:
        f.write(f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "mixed-package"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]

[tool.hwh.cython]
language = "c"
""")

    test_script = package_dir / "test_import.py"
    test_script.write_text("""
from mixedpkg import fast_core_func, slow_util_func
assert fast_core_func() == slow_util_func()
print("kiitos")
""")

    try:
        arguments = ["pip", "install", *pip_arguments, str(package_dir)]
        run_in_venv(
            venv_dir,
            arguments,
            show_output=True,
        )

        verify_installation(venv_dir, test_script, "kiitos")

    except subprocess.CalledProcessError as e:
        print("\nTest failed")
        print("Output:", e.output)
        print("Error:", e.stderr)
        raise
