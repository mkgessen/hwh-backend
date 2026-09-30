from pathlib import Path

import pytest

from .utils.package_utils import create_test_package
from .utils.venv_utils import create_virtual_env, setup_test_env


@pytest.fixture
def backend_dir() -> Path:
    """Get the backend package directory."""
    return Path(__file__).parent.parent.absolute()


@pytest.fixture
def fixture_dir() -> Path:
    """Get the test fixtures directory."""
    return Path(__file__).parent / "integration" / "fixtures"


@pytest.fixture
def test_env(tmp_path, backend_dir):
    """Create and set up test environment."""
    venv_dir = create_virtual_env(tmp_path)
    setup_test_env(venv_dir, backend_dir)
    return venv_dir


@pytest.fixture
def simple_cython_package(tmp_path, backend_dir):
    """Create a simple test package with Cython code."""
    cython_files = {
        "simple.pyx": """
def hello():
    return "Hello from Cython!"
"""
    }

    return create_test_package(
        tmp_path, "test_pkg", cython_files, backend_dir, pkg_dir_name=None
    )


@pytest.fixture
def sample_pyproject():
    """Sample pyproject.toml content for testing."""
    return """
[build-system]
requires = [
    "hwh-backend",
    "Cython>=3.1.0"
]
build-backend = "hwh_backend.build"

[project]
name = "test_pkg"
version = "0.1.0"
requires-python = ">=3.11"

[tool.hwh.cython.modules]
include_dirs = ["first", "second"]
runtime_library_dirs = ["/usr/lib"]
library_dirs = ["/usr/lib", "/home/user/lib"]
sources = ["foo.pyx", "bar.pyx"]
exclude_dirs = ["this", "that"]

[tool.hwh.cython]
language="c"
annotate=false

[tool.hwh.cython.compiler_directives]
binding = false
boundscheck = false
wraparound = false
initializedcheck = false
nonecheck = false
overflowcheck = false
embedsignature = false
cdivision = false
cdivision_warnings = false
profile = false
linetrace = false
type_version_tag = true
"""
