import pytest
from pathlib import Path
from unittest.mock import patch

from hwh_backend.build import (
    BdistWheelCommand,
    _parse_build_settings,
    _collect_pyx_paths,
)


@pytest.mark.parametrize(
    "sources,exclude_dirs,package_paths,file_structure,expected_count",
    [
        (
            ["test_project/a.pyx"],
            ["foo"],
            ["test_project"],
            {"test_project/": ["foo.pyx", "a.pyx", "x.pyx"]},
            1
        ),
        (
            # sources
            None,
            # exclude_dirs
            ["test_project/foo/"],
            # package_paths
            ["test_project", "test_project/include_me", "test_project/foo"],
            # file structure
            {
                "test_project/": ["foo.pyx", "a.pyx"],
                "test_project/include_me": ["pick.pyx"],
                "test_project/foo": ["skip.pyx"],
            },
            # num expected files after _collect_pyx_paths()
            3,
        ),
        (
            None,
            None,
            ["test_project", "test_project/sub"],
            {
                "test_project/": ["a.pyx", "b.pyx"],
                "test_project/sub/": ["c.pyx", "d.pyx"],
            },
            4,
        ),
    ],
)
def test_collect_pyx_paths_combinations(
        tmp_path, sources, exclude_dirs, package_paths, file_structure, expected_count
):
    # Create test structure
    for dir_path, files in file_structure.items():
        full_dir = tmp_path / dir_path
        full_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            (full_dir / f).touch()

    package_paths = [tmp_path/pkg for pkg in package_paths]
    sources = [tmp_path/src for src in sources] if sources else None
    exclude_dirs = [tmp_path/excl for excl in exclude_dirs] if exclude_dirs else None
    result = _collect_pyx_paths(package_paths, sources=sources, exclude_dirs=exclude_dirs)
    print(result)
    assert len(result) == expected_count


def test_parse_build_settings():
    settings = {"annotate": "true", "nthreads": "4", "force": "false"}
    parsed = _parse_build_settings(settings)
    assert parsed["annotate"] is True
    assert parsed["nthreads"] == 4
    assert parsed["force"] is False


def test_parse_invalid_build_settings():
    settings = {"annotate": "true", "nthreads": "invalid", "force": "false"}
    parsed = _parse_build_settings(settings)
    assert "nthreads" not in parsed


def test_parse_empty_build_settings():
    assert _parse_build_settings(None) == {}


def test_bdist_wheel_command_should_not_define_run():
    # run() only called super() — no reason to override it
    assert "run" not in BdistWheelCommand.__dict__


def test_bdist_wheel_command_finalize_options_should_preserve_user_options():
    # Arrange — user_options is a class-level list of option tuples defined by wheel
    from setuptools.dist import Distribution
    dist = Distribution({"name": "test-pkg", "version": "0.1.0"})
    cmd = BdistWheelCommand(dist)
    expected_user_options = BdistWheelCommand.user_options

    # Act — mock super() so we only execute our finalize_options body
    with patch.object(BdistWheelCommand.__bases__[0], "finalize_options"):
        cmd.finalize_options()

    # Assert — user_options must not be overwritten with config_settings
    assert cmd.user_options is expected_user_options
