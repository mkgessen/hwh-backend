import pytest
from pathlib import Path

from hwh_backend.build import (
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
