import subprocess
from pathlib import Path

import pytest

from hwh_backend.parser import PyProject

from ..utils.package_utils import create_package_structure, create_test_package
from ..utils.venv_utils import create_virtual_env, run_in_venv, setup_test_env
from ..utils.verification_utils import verify_editable_install, verify_installation


@pytest.fixture
def package_test_dir(tmp_path):
    """Create a test directory with a package structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create test package structure
    package_tree = {
        "src": {
            "mypackage": {
                "subpkg1": ["module1.py", "cython1.pyx"],
                "subpkg2": ["module2.py", "cython2.pyx"],
            }
        }
    }
    create_package_structure(project_dir, package_tree, is_src_parent=True)
    return project_dir


def test_src_layout_structure(tmp_path):
    """Test that src layout is created correctly with __init__.py files in the right places."""
    package_tree = {
        "src": {
            "mypackage": {"core": ["base.pyx", "utils.py"], "utils": ["helpers.py"]}
        }
    }

    create_package_structure(tmp_path, package_tree, is_src_parent=True)

    # src directory should not have __init__.py
    assert not (tmp_path / "src" / "__init__.py").exists()

    # Package and its subdirectories should have __init__.py
    assert (tmp_path / "src" / "mypackage" / "__init__.py").exists()
    assert (tmp_path / "src" / "mypackage" / "core" / "__init__.py").exists()
    assert (tmp_path / "src" / "mypackage" / "utils" / "__init__.py").exists()

    # Check other files exist
    assert (tmp_path / "src" / "mypackage" / "core" / "base.pyx").exists()
    assert (tmp_path / "src" / "mypackage" / "core" / "utils.py").exists()
    assert (tmp_path / "src" / "mypackage" / "utils" / "helpers.py").exists()


def test_package_discovery_explicit(package_test_dir, tmp_path):
    """Test explicit package listing in setuptools config."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    with open(package_test_dir / "pyproject.toml", "w") as f:
        f.write(f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "mypackage"
version = "0.1.0"

[tool.setuptools.packages.find]
where = ["src"]
""")

    project = PyProject(package_test_dir)
    assert set(project.packages) == {
        "mypackage",
        "mypackage.subpkg1",
        "mypackage.subpkg2",
    }


def test_package_discovery_find(package_test_dir, tmp_path):
    """Test package discovery using find configuration."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    with open(package_test_dir / "pyproject.toml", "w") as f:
        f.write(f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "mypackage"
version = "0.1.0"

[tool.setuptools.packages.find]
where = ["src"]
exclude = ["mypackage.subpkg2*"]


""")

    project = PyProject(package_test_dir)
    discovered = set(project.packages)
    print(f"Discovered {discovered}")
    assert "mypackage" in discovered
    assert "mypackage.subpkg1" in discovered
    assert "mypackage.subpkg2" not in discovered


def test_package_discovery_default_src_layout(package_test_dir, tmp_path):
    """Test default package discovery behavior with no configuration."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    with open(package_test_dir / "pyproject.toml", "w") as f:
        f.write(f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "mypackage"
version = "0.1.0"
""")

    project = PyProject(package_test_dir)
    assert project.packages == []


def test_package_discovery_default_flat_layout(tmp_path):
    """Test default package discovery behavior with no configuration."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create test package structure
    package_tree = {
        "otherpackage": {
            "subpkg1": ["module1.py", "cython1.pyx"],
            "subpkg2": ["module2.py", "cython2.pyx"],
        }
    }
    create_package_structure(project_dir, package_tree)

    with open(project_dir / "pyproject.toml", "w") as f:
        f.write(f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "mypackage"
version = "0.1.0"
""")

    project = PyProject(project_dir)
    assert sorted(project.packages) == sorted(["otherpackage", "otherpackage.subpkg1", "otherpackage.subpkg2"])


def test_package_discovery_different_names(package_test_dir):
    """Test package discovery when project name differs from package directory name."""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    # Create package structure
    package_tree = {
        "coolproject": {  # Actual importable package name
            "core.pyx": "",
            "utils.py": "",
        }
    }
    create_package_structure(package_test_dir, package_tree)

    # Create pyproject.toml with different project name
    with open(package_test_dir / "pyproject.toml", "w") as f:
        f.write(f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "my-cool-project"  # Different from package name
version = "0.1.0"

[tool.setuptools.packages.find]
# where = ["src"]
include = ["coolproject"]


""")

    # Test the package discovery
    project = PyProject(package_test_dir)

    # Test 1: Basic package discovery
    assert project.packages == ["coolproject"]

    # Test 2: Project name is different from package name
    assert project.package_name == "my-cool-project"
    assert project.packages[0] != project.package_name

    # Test 3: Package path resolution
    package_path = project.get_package_path("coolproject")
    assert package_path == package_test_dir / "coolproject"
    assert (package_path / "__init__.py").exists()
    assert (package_path / "core.pyx").exists()

    # Test 4: All package paths
    all_paths = project.get_all_package_paths()
    assert len(all_paths) == 1
    assert all_paths[0] == package_test_dir / "coolproject"


def test_different_names_installation(tmp_path):
    """Test installation of a package where project name differs from package name.
    e.g. pkg-name, but pkg_name as a dir"""
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    # Create test environment with explicit backend path
    venv_dir = create_virtual_env(tmp_path / "venv")
    setup_test_env(venv_dir, backend_dir)

    # Create Cython file content
    cython_files = {
        "core.pyx": """
cpdef get_message():
    return "Hello from coolproject Cython module"
"""
    }

    # Create package with different project/package names
    package_dir = create_test_package(
        tmp_path,
        "my-cool-project",  # Project name
        cython_files,
        backend_dir,
        pkg_dir_name="coolproject",  # Actual package name
    )

    # Create test script
    test_script = package_dir / "scripts" / "test_import.py"
    test_script.write_text("""
from coolproject.core import get_message

result = get_message()
assert result == "Hello from coolproject Cython module"
print("Import test passed!")
""")

    try:
        # NOTE: Can't test regular install w/o --no-build-isolation
        # because the isolated environment will pull everything from PyPI
        run_in_venv(
            venv_dir,
            ["pip", "install", "--no-build-isolation", str(package_dir)],
            show_output=True,
        )
        verify_installation(venv_dir, test_script, "Import test passed!")

        # Test editable installation
        editable_env = create_virtual_env(tmp_path / "editable_env")
        setup_test_env(editable_env, backend_dir)

        run_in_venv(
            editable_env, ["pip", "install", "-e", str(package_dir)], show_output=True
        )

        # Test modification in editable mode
        source_file = package_dir / "coolproject" / "core.pyx"
        original_content = source_file.read_text()
        modified_content = original_content.replace(
            "Hello from coolproject", "Modified hello from coolproject"
        )

        modified_test_script = package_dir / "scripts" / "test_modified.py"
        modified_test_script.write_text("""
from coolproject.core import get_message

result = get_message()
assert result == "Modified hello from coolproject Cython module"
print("Modified test passed!")
""")

        verify_editable_install(
            editable_env,
            package_dir,
            source_file,
            original_content,
            modified_content,
            modified_test_script,
            "Modified test passed!",
        )

    except subprocess.CalledProcessError as e:
        print("\nTest failed")
        print("Output:", e.output)
        print("Error:", e.stderr)
        raise
