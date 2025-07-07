import dataclasses
import tomllib
import warnings
from collections import defaultdict
from collections.abc import Mapping, Sequence
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional, TypeAlias

from packaging.requirements import Requirement
from packaging.version import Version
from pyproject_metadata import StandardMetadata
from setuptools import find_packages

from .hwh_config import HwhConfig


@dataclasses.dataclass(frozen=True)
class PackageList:
    packages: list[str]


@dataclasses.dataclass(frozen=True)
class FindConfig:
    cfg: dict


class AutoDiscover:
    pass


SetuptoolsPackageConfig: TypeAlias = FindConfig | PackageList | AutoDiscover


class PyProject:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.pyproject_path = project_dir / "pyproject.toml"
        if not self.pyproject_path.exists():
            raise FileNotFoundError(
                f"Couldn't locate pyproject.toml from {str(self.project_dir)}"
            )
        self._data: Optional[Dict[str, Any]] = None
        # This is set in _discover_packages, called by the packages property
        self._package_where: Optional[Mapping[str, str]] = None

    @property
    def toml(self):
        if self._data:
            return self._data

        if not self.pyproject_path.exists():
            raise FileNotFoundError(f"No pyproject.toml found in {self.project_dir}")

        with open(self.pyproject_path, "rb") as f:
            self._data = tomllib.load(f)

        return self._data

    @property
    def metadata(self) -> StandardMetadata:
        return StandardMetadata.from_pyproject(self.toml)

    @property
    def runtime_dependencies(self) -> Sequence[Requirement]:
        """Runtime dependencies of the package."""
        install_requires = self.setuptools_config.get("install_requires")

        dependencies = self.toml["project"].get("dependencies")

        if install_requires is not None:
            if dependencies is None:
                warnings.warn(
                    "Should rename setuptools.install_requires with project.dependencies"
                )
                return list(map(Requirement, install_requires))

            warnings.warn(
                "Found both project.dependencies and setuptools.install_requires."
                "Using project.dependencies"
            )

        return list(map(Requirement, dependencies)) if dependencies else []

    @property
    def build_requires(self) -> Sequence[Requirement]:
        """Build-time dependencies of the package."""
        build_requires = self.toml.get("build-system", {}).get("requires", [])
        return list(map(Requirement, build_requires))

    @property
    def all_dependencies(self) -> Sequence[Requirement]:
        """Run- and build-time dependencies of the package."""
        return self.build_requires + self.runtime_dependencies

    @property
    def package_name(self) -> str:
        """Get the package name from pyproject.toml"""
        return self.metadata.name

    @property
    def package_version(self) -> Optional[Version]:
        """Get the package version from pyproject.toml"""
        # NOTE: Do not use StandardMetadata as it parses a missing version
        #       as "0.0.0" (???)
        return self.toml["project"].get("version")

    def get_hwh_config(self) -> HwhConfig:
        # TODO: switch to property
        return HwhConfig(self.toml)

    @property
    def setuptools_config(self) -> dict:
        """Get setuptools configuration from pyproject.toml."""
        return self.toml.get("tool", {}).get("setuptools", {})

    @cached_property
    def setuptools_package_config(self) -> SetuptoolsPackageConfig:
        cfg = self.setuptools_config
        try:
            packages = cfg.pop("packages")
        except KeyError:
            return AutoDiscover()

        if isinstance(packages, list):
            return PackageList(packages)

        try:
            find_cfg = packages["find"]
        except KeyError:
            raise TypeError(
                "setuptools.packages must be list or find configuration. "
                "See https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration"
            )

        if not isinstance(find_cfg, dict):
            raise TypeError("setuptools.packages.find must be table.")
        return FindConfig(find_cfg)

    @property
    def entrypoints(self) -> dict[str, list[str]]:
        # TODO: Handle dynamic entrypoints
        def dict_to_list(d):
            return [f"{k}={v}" for k, v in d.items()]

        entrypoints = self.metadata.entrypoints

        if self.metadata.scripts:
            entrypoints["console_scripts"] = self.metadata.scripts
        if self.metadata.gui_scripts:
            entrypoints["gui_scripts"] = self.metadata.gui_scripts

        return {name: dict_to_list(group) for name, group in entrypoints.items() if group}

    @property
    def package_dir(self) -> dict:
        """Get package directory mapping from setuptools config."""
        return self.setuptools_config.get("package-dir", {})

    @property
    def discovered_package_dir(self) -> dict:
        return {pkg: self.get_package_path(pkg) for pkg in self.packages}

    @cached_property
    def packages(self) -> list[str]:
        """Get list of packages to include."""
        return self._discover_packages()

    def _discover_packages(self) -> list[str]:
        """Discover packages using setuptools.packages.find configuration."""
        setuptools_config = self.setuptools_config

        def rooted_find_packages(where=".", **kargs):
            return find_packages(**kargs, where=self.project_dir / where)

        # May overwrite this later
        self._package_where = defaultdict(lambda: ".")

        match self.setuptools_package_config:
            case PackageList(packages=pkgs):
                return pkgs
            case AutoDiscover():
                return rooted_find_packages()
            case FindConfig(cfg=cfg):
                try:
                    where_cfg = cfg.pop("where")
                except KeyError:
                    return rooted_find_packages(**cfg)

                if isinstance(where_cfg, str):
                    where_cfg = [where_cfg]

                self._package_where = {
                    package: where
                    for where in where_cfg
                    for package in rooted_find_packages(where=where, **cfg)
                }
                return list(self._package_where)

            case _:
                raise TypeError("Bug in setuptools_package_config")

    def get_package_path(self, package: str) -> Path:
        """Convert a package name to its directory path."""
        # HACK: Make sure we compute the list of packages if needed
        self.packages
        return (
            self.project_dir / self._package_where[package] / package.replace(".", "/")
        )

    def get_all_package_paths(self) -> list[Path]:
        """Get paths for all configured packages."""
        return [self.get_package_path(pkg) for pkg in self.packages]
