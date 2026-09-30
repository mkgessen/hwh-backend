import shutil
from pathlib import Path
from typing import Dict, List, Optional


def create_pyproject_toml(
    pkg_dir: Path,
    pkg_name: str,
    backend_dir: Path,
    dependencies: Optional[List[str]] = None,
    version: str = "0.1.0",
    pkg_dir_name: Optional[str] = None,
) -> None:
    """Create a pyproject.toml file with setuptools.packages.find section."""
    content = f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython>=3.1.0"
]
build-backend = "hwh_backend.build"

[project]
name = "{pkg_name}"
version = "{version}"
requires-python = ">=3.11"
"""
    if dependencies:
        content += "dependencies = [\n"
        for dep in dependencies:
            content += f'    "{dep}",\n'
        content += "]\n"

    # Write setuptools section
    if pkg_dir_name:
        content += f"""
[tool.setuptools.packages.find]
where = ["."]  # or ["src"] if using src layout
include = ["{pkg_dir_name}*"]  # includes subpackages
"""
    else:
        content += """
[tool.setuptools.packages.find]
where = ["."]  # or ["src"] if using src layout
"""

    content += """
[tool.hwh.cython]
language = "c"
compiler_directives = {  }
"""

    with open(pkg_dir / "pyproject.toml", "w") as f:
        f.write(content)


def create_test_package(
    base_dir: Path,
    project_name: str,
    cython_files: Dict[str, str],
    backend_dir: Path,
    dependencies: Optional[List[str]] = None,
    pkg_dir_name: Optional[str] = None,
) -> Path:
    """Create a test package with specified Cython files."""
    pkg_dir = base_dir / project_name
    pkg_dir.mkdir(parents=True)

    # Use pkg_dir_name if provided, otherwise use project_name
    import_name = pkg_dir_name or project_name.replace("-", "_")

    # Create package directory
    src_dir = pkg_dir / import_name
    src_dir.mkdir()

    # Add empty scripts dir for tests. Might use it?
    script_dir = pkg_dir / "scripts"
    script_dir.mkdir()

    # Create Cython files
    for file_path, content in cython_files.items():
        full_path = src_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    (src_dir / "__init__.py").write_text("")

    create_pyproject_toml(
        pkg_dir, project_name, backend_dir, dependencies, pkg_dir_name=import_name
    )

    (pkg_dir / "README.md").write_text(f"# {project_name}\nTest package")

    # Create MANIFEST.in with Cython files. Needs README for pip wheel not to nag
    manifest_content = f"""
include README.md
recursive-include {import_name} *.pxd
recursive-include {import_name} *.pyx
"""
    (pkg_dir / "MANIFEST.in").write_text(manifest_content)

    return pkg_dir


def copy_test_package(
    src_pkg: str,
    dest_dir: Path,
    fixture_dir: Path,
    backend_dir: Path,
    dependencies: Optional[List[str]] = None,
    pkg_dir_name: Optional[str] = None,
) -> Path:
    """Copy a test package from fixtures directory."""
    src_path = fixture_dir / src_pkg
    dest_path = dest_dir / src_pkg

    shutil.copytree(src_path, dest_path)
    create_pyproject_toml(
        dest_path, src_pkg, backend_dir, dependencies, pkg_dir_name=pkg_dir_name
    )

    return dest_path


def create_package_structure(
    base_dir: Path,
    package_tree: dict,
    add_init: bool = True,
    is_src_parent: bool = False,
):
    """Create a package directory structure for testing.
    Example:
        package_tree = {
            "src": {  # Won't get __init__.py
                "mypackage": {  # Will get __init__.py
                    "core": ["base.pyx", "utils.py"]
                }
            }
        }
    """
    for name, contents in package_tree.items():
        pkg_dir = base_dir / name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Add __init__.py only if we're not in src or another parent dir
        if add_init and not is_src_parent:
            print(f"__init__ to {str(pkg_dir)}")
            (pkg_dir / "__init__.py").touch()

        if isinstance(contents, dict):
            # Check if this is a src directory or we're already in parent mode
            # next_is_parent = is_src_parent or name == "src"
            next_is_parent = False

            # It's either a subdirectory dict or file content dict
            if any(isinstance(v, (dict, list)) for v in contents.values()):
                # It's a subdirectory structure
                create_package_structure(
                    pkg_dir, contents, add_init=add_init, is_src_parent=next_is_parent
                )
            else:
                # It's a dict of files with content
                for fname, content in contents.items():
                    (pkg_dir / fname).write_text(str(content))
        elif isinstance(contents, list):
            for file in contents:
                (pkg_dir / file).touch()
