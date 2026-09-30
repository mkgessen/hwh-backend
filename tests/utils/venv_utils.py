import subprocess
import sys
import venv
from pathlib import Path
from typing import Optional


def create_virtual_env(tmp_path: Path) -> Path:
    """Create a virtual environment for testing installations."""
    venv_dir = tmp_path / "env"
    venv.create(venv_dir, with_pip=True)
    return venv_dir


def get_venv_python(venv_dir: Path) -> str:
    """Get path to Python executable in virtual environment."""
    if sys.platform == "win32":
        return str(venv_dir / "Scripts" / "python.exe")
    return str(venv_dir / "bin" / "python")


def run_in_venv(
    venv_dir: Path,
    commands: list[str],
    show_output: bool = False,
    cwd: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Run commands in virtual environment."""
    python = get_venv_python(venv_dir)

    if commands[0] == "pip":
        full_command = [python, "-m"] + commands
        if "-v" not in commands:
            full_command.append("-v")
    elif commands[0] == "python":
        if len(commands) > 2 and commands[1] == "-m":
            full_command = [python, "-m"] + commands[2:]
        else:
            full_command = [python] + commands[1:]
    else:
        # TODO: change this so that the else option is whatever binary - not python
        full_command = [python, "-m"] + commands

    print(f"Running command: {' '.join(map(str, full_command))}")
    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
    )

    if show_output:
        print("\nOutput:", result.stdout)
        if result.stderr:
            print("Error:", result.stderr)
    return result


def setup_test_env(venv_dir: Path, backend_dir: Optional[Path] = None) -> None:
    """Set up test environment with backend package."""
    if backend_dir is None:
        backend_dir = Path(__file__).parent.parent.parent.parent.absolute()

    run_in_venv(
        venv_dir,
        [
            "pip",
            "install",
            "setuptools",
            "wheel",
            "Cython>=3.1.0",
            "pyproject-metadata",
            "build",
        ],
    )

    run_in_venv(venv_dir, ["pip", "install", "--no-deps", str(backend_dir)])
    run_in_venv(venv_dir, ["pip", "install", f"{backend_dir}[all]"])
