import shutil
import subprocess
from pathlib import Path

from .test_installation import create_virtual_env, run_in_venv, setup_test_env

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sample_package"


def copy_sample_package(dest_dir: Path, backend_dir: Path) -> Path:
    """Copy the sample package to test directory and set up pyproject.toml."""
    dest_path = dest_dir / "sample_package"

    # Copy the Cython source files
    shutil.copytree(FIXTURE_DIR, dest_path / "sample_package")

    # Create pyproject.toml
    content = f"""
[build-system]
requires = [
    "hwh-backend @ file://{backend_dir}",
    "Cython<3.0.0"
]
build-backend = "hwh_backend.build"

[project]
name = "sample_package"
version = "0.1.0"
requires-python = ">=3.11"

[tool.hwh.cython]
language = "c"
compiler_directives = {{ language_level = "3" }}
"""

    with open(dest_path / "pyproject.toml", "w") as f:
        f.write(content)

    return dest_path


def create_test_script(script_dir: Path) -> Path:
    """Create a test script that imports and verifies nested modules."""
    script = script_dir / "verify_nested_imports.py"
    script.write_text("""
from sample_package.core.base import BaseOp
from sample_package.utils.helpers import Helper
from sample_package.extensions.advanced import Advanced
from sample_package.extensions.specialized.expert import Expert

# Test the entire dependency chain
base_op = BaseOp(2.0)
helper = Helper(base_op)
advanced = Advanced(helper)
expert = Expert(advanced, BaseOp(3.0))

# Test computation through the hierarchy
result = expert.deep_process()
expected = ((3.0 * 2.0 + 1.0) * 3.0 + (2.0 * 2.0)) * 2.0
assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"

print("All nested module tests passed!")
""")
    return script


def test_nested_cython_modules(tmp_path):
    """Test building and using packages with nested Cython modules."""
    venv_dir = create_virtual_env(tmp_path / "venv")
    setup_test_env(venv_dir)
    backend_dir = Path(__file__).parent.parent.parent.absolute()

    package_dir = copy_sample_package(tmp_path, backend_dir)
    test_script = create_test_script(tmp_path)

    try:
        # Regular installation
        run_in_venv(venv_dir, ["pip", "install", "--upgrade", "pip"])
        run_in_venv(venv_dir, ["pip", "install", str(package_dir)], show_output=True)
        result = run_in_venv(venv_dir, ["python", str(test_script)])
        assert "All nested module tests passed!" in result.stdout

        # Editable installation in new venv
        venv_dir_editable = create_virtual_env(tmp_path / "venv_editable")
        setup_test_env(venv_dir_editable)
        run_in_venv(
            venv_dir_editable,
            ["pip", "install", "-e", str(package_dir)],
            show_output=True,
        )
        result = run_in_venv(venv_dir_editable, ["python", str(test_script)])
        assert "All nested module tests passed!" in result.stdout

        # Test python -m build in separate venv
        build_venv = create_virtual_env(tmp_path / "venv_build")
        setup_test_env(build_venv)
        run_in_venv(
            build_venv,
            ["python", "-m", "build", "--no-isolation"],
            cwd=str(package_dir),
        )

        # Verify the wheel
        wheel_path = next((package_dir / "dist").glob("*.whl"))
        run_in_venv(venv_dir, ["pip", "install", str(wheel_path)])
        result = run_in_venv(venv_dir, ["python", str(test_script)])
        assert "All nested module tests passed!" in result.stdout

    except subprocess.CalledProcessError as e:
        print("\nTest failed")
        print("Output:", e.output)
        print("Error:", e.stderr)
        raise
