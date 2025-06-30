from pathlib import Path

from hwh_backend.parser import PyProject

from ..utils.package_utils import create_package_structure


def test_src_layout_discovery(tmp_path):
    """Test package discovery with src layout."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    package_tree = {
        "src": {
            "mypackage": {
                "core": {
                    "base.pyx": "# Some Cython code",
                },
                "utils": {
                    "helpers.py": "# Pure Python module",
                },
            }
        }
    }
    create_package_structure(project_dir, package_tree, is_src_parent=True)

    with open(project_dir / "pyproject.toml", "w") as f:
        f.write("""
[build-system]
requires = ["hwh-backend"]
build-backend = "hwh_backend.build"

[project]
name = "mypackage"
version = "0.1.0"

[tool.setuptools.packages.find]
where = ["src"]
include = ["mypackage*"]
""")

    project = PyProject(project_dir)
    packages = project.packages

    assert "mypackage" in packages
    assert "mypackage.core" in packages
    assert "mypackage.utils" in packages


# FIXME: the test below doesn't work because create_package_structure is crap

# def test_src_layout_with_namespace(tmp_path):
#     project_dir = tmp_path / "test_project"
#     project_dir.mkdir()
#
#     # Create namespace package structure
#     package_tree = {
#         "src": {
#             "company": {
#                 "package": {
#                     "core.pyx": "# Cython module",
#                 }
#             }
#         }
#     }
#     create_package_structure(project_dir, package_tree, is_src_parent=True)
#
#     with open(project_dir / "pyproject.toml", "w") as f:
#         f.write("""
# [build-system]
# requires = ["hwh-backend"]
# build-backend = "hwh_backend.build"
#
# [project]
# name = "company-package"
# version = "0.1.0"
#
# [tool.setuptools.packages.find]
# where = ["src"]
# include = ["company.*"]
# """)
#
#     project = PyProject(project_dir)
#     packages = project.packages
#
#     assert "company" in packages
#     assert "company.package" in packages
#


def test_src_layout_with_exclusions(tmp_path):
    """Test package discovery with src layout and exclusion patterns."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    package_tree = {
        "src": {
            "mypackage": {
                "core": {
                    "base.pyx": "# Cython code",
                },
                "tests": {
                    "test_core.py": "# Test module",
                },
                "experimental": {
                    "unstable.pyx": "# Experimental code",
                },
            }
        }
    }
    create_package_structure(project_dir, package_tree, is_src_parent=True)

    with open(project_dir / "pyproject.toml", "w") as f:
        f.write("""
[build-system]
requires = ["hwh-backend"]
build-backend = "hwh_backend.build"

[project]
name = "mypackage"
version = "0.1.0"

[tool.setuptools.packages.find]
where = ["src"]
exclude = ["mypackage*tests", "mypackage*experimental"]
""")

    project = PyProject(project_dir)
    packages = project.packages

    assert "mypackage" in packages
    assert "mypackage.core" in packages
    assert "mypackage.tests" not in packages
    assert "mypackage.experimental" not in packages


def test_src_layout_package_dir_resolution(tmp_path):
    """Test package path resolution with src layout."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    package_tree = {
        "src": {
            "mypackage": {
                "core.pyx": "# Cython module",
            }
        }
    }
    create_package_structure(project_dir, package_tree, is_src_parent=True)

    with open(project_dir / "pyproject.toml", "w") as f:
        f.write("""
[build-system]
requires = ["hwh-backend"]
build-backend = "hwh_backend.build"

[project]
name = "mypackage"
version = "0.1.0"

[tool.setuptools.packages.find]
where = ["src"]
include = ["mypackage*"]
""")

    project = PyProject(project_dir)
    package_path = project.get_package_path("mypackage")
    print(f"Package path = {package_path}")

    # Should resolve to src/mypackage
    assert package_path.relative_to(project_dir) == Path("src/mypackage")
    assert (package_path / "core.pyx").exists()
