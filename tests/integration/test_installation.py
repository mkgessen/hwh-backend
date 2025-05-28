from ..utils.package_utils import create_test_package
from ..utils.venv_utils import run_in_venv
from ..utils.verification_utils import verify_editable_install, verify_installation


def test_basic_installation(test_env, simple_cython_package):
    """Test basic package installation."""
    verify_script = """
from test_pkg.simple import hello
assert hello() == "Hello from Cython!"
print("Installation successful!")
"""
    script_path = simple_cython_package / "scripts/verify.py"
    script_path.write_text(verify_script)

    run_in_venv(test_env, ["pip", "install", str(simple_cython_package)])
    verify_installation(test_env, script_path, "Installation successful!")


def test_editable_installation(test_env, simple_cython_package):
    """Test editable package installation."""
    source_file = simple_cython_package / "test_pkg" / "simple.pyx"
    original = source_file.read_text()
    modified = original.replace(
        'return "Hello from Cython!"', 'return "Modified hello from Cython!"'
    )

    verify_script = """
from test_pkg.simple import hello
assert hello() == "Modified hello from Cython!"
print("Editable install works!")
"""
    script_path = simple_cython_package / "verify_modified.py"
    script_path.write_text(verify_script)

    run_in_venv(test_env, ["pip", "install", "-e", str(simple_cython_package)])
    verify_editable_install(
        test_env,
        simple_cython_package,
        source_file,
        original,
        modified,
        script_path,
        "Editable install works!",
    )


def test_build_command(test_env, simple_cython_package):
    """Test python -m build command."""
    run_in_venv(
        test_env,
        ["python", "-m", "build", "--wheel", "--no-isolation"],
        cwd=str(simple_cython_package),
    )

    wheel = next((simple_cython_package / "dist").glob("*.whl"))
    print(f"Installing wheel with {str(wheel)}")
    run_in_venv(test_env, ["pip", "install", str(wheel)])

    verify_script = """
from test_pkg.simple import hello
assert hello() == "Hello from Cython!"
print("Wheel installation successful!")
"""
    script_path = simple_cython_package / "scripts/verify_wheel.py"
    script_path.write_text(verify_script)
    verify_installation(test_env, script_path, "Wheel installation successful!")


def test_dependency_installation(test_env, tmp_path, backend_dir):
    # Create a simple package with dependencies
    cython_files = {
        "simple.pyx": """
def dependencies_available():
    import numpy as np
    import pandas as pd
    return "Dependencies OK"
"""
    }

    # Create test package with specific dependencies
    package_dir = create_test_package(
        tmp_path,
        "dependency-test",
        cython_files,
        backend_dir,
        dependencies=["numpy>=1.20.0", "pandas>=1.3.0"],
    )

    run_in_venv(
        test_env,
        ["pip", "install", str(package_dir), "--no-build-isolation"],
        show_output=True,
    )

    pip_freeze = run_in_venv(test_env, ["pip", "freeze"])
    assert "numpy==" in pip_freeze.stdout
    assert "pandas==" in pip_freeze.stdout
