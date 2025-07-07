import setuptools  # This must come before importing Cython!
import json
import shutil
import site
import sysconfig
import warnings
from collections.abc import Sequence
from itertools import chain
from importlib.metadata import distributions
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from Cython.Build import cythonize
from setuptools.build_meta import (
    build_editable as _build_editable,
)
from setuptools.command.build_ext import build_ext
from setuptools.dist import Distribution
from setuptools.extension import Extension

from hwh_backend.hwh_config import SitePackages

from .logger import logger, setup_logging
from .parser import PyProject

# Global flag to prevent double builds
_EXTENSIONS_BUILT = False

# Global flag to pass --config-setting foo=bar values from python -m build
_CONFIG_OPTIONS: Optional[dict[str, int | bool]] = None


def _is_editable_install():
    """Inspects package's site_packages/pkg_name/direct_url.json
    to dermine whether the installation is editable or not, see
    https://packaging.python.org/en/latest/specifications/direct-url-data-structure/"""
    project = PyProject(Path())
    pkg_name = project.package_name

    logger.debug(f"===CHECKING EDITABLE=== for package {pkg_name}")
    # FIXME: using all site packages here might not be clever..
    site_packages = site.getsitepackages()
    logger.debug(f"Used site packages: {site_packages}")
    for dist in distributions(name=pkg_name, path=site_packages):
        content = dist.read_text("direct_url.json")
        logger.debug(f"Found content {content}")
        if content is not None:
            direct_url = json.loads(content)
            logger.debug(f"Converting to json {direct_url}")
            if "dir_info" in direct_url:
                logger.debug(f"[OK] Package {pkg_name} is editable install")
                return direct_url["dir_info"].get("editable", False)

    logger.debug(f"Package {pkg_name} is not editable install")
    return False


def get_sitepackages(option: SitePackages):
    # TODO: move to hwh config
    match option:
        case SitePackages.PURELIB:
            return [sysconfig.get_path("purelib")]
        case SitePackages.USER:
            return [site.getusersitepackages()]
        case SitePackages.SITE:
            return site.getsitepackages()
        case SitePackages.NONE:
            return []




def resolve_package_path(
    pyx_file: Path, package_paths: List[Path]
) -> Optional[tuple[str, Path]]:
    """Resolve a .pyx file to its package name and relative path."""
    return next(
        (
            (pkg_path.name, pyx_file.relative_to(pkg_path))
            for pkg_path in package_paths
            if pyx_file.is_relative_to(pkg_path)
        ),
        None,
    )


def _get_ext_modules(project: PyProject, config_settings: Optional[dict] = None):
    """Get Cython extension modules configuration."""
    logger.debug("=== Starting _get_ext_modules ===")
    logger.debug(f"Project name: {project.package_name}")
    logger.debug(f"Project version: {project.package_version}")
    logger.debug(f"get ext Config settings: {config_settings}")

    # Parse build settings
    global _CONFIG_OPTIONS
    if not _CONFIG_OPTIONS:
        _CONFIG_OPTIONS = _parse_build_settings(config_settings)

    logger.debug(f"Parsed build settings: {_CONFIG_OPTIONS}")

    # Create directory lists for Extension ctor and cythonize()
    config = project.get_hwh_config().cython
    site_packages = get_sitepackages(config.site_packages)
    logger.debug(f"Site packages: {site_packages}")

    library_dirs = config.library_dirs + site_packages
    runtime_library_dirs = config.runtime_library_dirs
    include_dirs = config.include_dirs + site_packages

    if config.use_numpy_include:
        try:
            import numpy

            include_dirs += [numpy.get_include()]
        except ModuleNotFoundError as e:
            logger.error(
                "Numpy headers requested, but numpy installation was not found"
            )
            raise ModuleNotFoundError from e

    logger.debug(f"Library dirs: {library_dirs}")
    logger.debug(f"Runtime library dirs: {runtime_library_dirs}")
    logger.debug(f"Include dirs: {include_dirs}")

    # Find all .pyx files in the package directory
    package_paths = project.get_all_package_paths()
    logger.debug(f"Package paths: {package_paths}")

    pyx_paths = _collect_pyx_paths(
        package_paths,
        config.sources,
        config.exclude_dirs
    )

    linetrace =  _CONFIG_OPTIONS.get("linetrace", False)
    extra_compile_args = config.extra_compile_args
    if linetrace:
        extra_compile_args += ["-DCYTHON_TRACE_NOGIL=1"]

    # Create Extensions
    ext_modules = []
    for pyx_path in pyx_paths:
        # Convert path to proper module path. Absolute paths are forbidden by pip
        logger.debug(f"\nProcessing: {pyx_path}")
        pkg_info = resolve_package_path(pyx_path, package_paths)
        if pkg_info is None:
            logger.warning(f"Could not determine package for {pyx_path}")

        pkg_name, rel_path = pkg_info
        logger.debug(f"Relative path: {rel_path}")

        # Construct full module path including package name
        module_parts = [pkg_name]
        if rel_path.parent != Path("."):
            module_parts.extend(part for part in rel_path.parent.parts)

        if rel_path.name != "__init__.pyx":
            module_parts.append(rel_path.stem)

        module_path = ".".join(module_parts)  # .split(".", 1)[-1]
        logger.debug(f"Constructed module path: {module_path}")
        logger.debug(f"Include directories: {config.include_dirs}")
        logger.debug(f"Linking libraries: {config.libraries}")
        ext = Extension(
            module_path,
            [str(pyx_path)],
            include_dirs=include_dirs,
            language=config.language,
            library_dirs=library_dirs,
            libraries=config.libraries,
            extra_compile_args=extra_compile_args,
            extra_link_args=config.extra_link_args,
            runtime_library_dirs=runtime_library_dirs,
        )
        logger.debug(f"Created Extension object: {ext.name}")
        ext_modules.append(ext)

    logger.debug(f"\nTotal extensions to build: {len(ext_modules)}")
    logger.debug("=== Finished _get_ext_modules ===\n")

    # Override config values with build settings.
    if not _CONFIG_OPTIONS:
        _CONFIG_OPTIONS = {}
    nthreads = _CONFIG_OPTIONS.get("nthreads", config.nthreads)
    force = _CONFIG_OPTIONS.get("force", config.force)
    annotate = _CONFIG_OPTIONS.get("annotate", config.annotate)

    compiler_directives = config.compiler_directives.as_dict()
    if linetrace:
        compiler_directives["linetrace"] = True

    logger.debug(f"\n=== FORCE = {force} ")
    logger.debug(f"\n=== ANNOTATE = {annotate} ")
    logger.debug(f"\n=== NTHREADS = {nthreads} ")
    logger.debug(f"\n=== LINETRACE = {linetrace} ")

    cythonized = cythonize(
        ext_modules,
        nthreads=nthreads,
        force=force,
        annotate=annotate,
        compiler_directives=compiler_directives,
        include_path=include_dirs,  # This helps find .pxd files
    )

    return cythonized


class EditableBuildExt(build_ext):
    """Custom build_ext that handles editable installs properly."""

    def initialize_options(self):
        super().initialize_options()
        self._is_editable = False
        self._original_build_lib = None

    def finalize_options(self):
        """Finalize build options and set up editable install if needed."""
        super().finalize_options()
        self._is_editable = _is_editable_install()

        if self._is_editable:
            logger.debug("Configuring for editable install")
            # Store original build_lib for later
            self._original_build_lib = self.build_lib
            # For editable install, build directly in source tree
            self.inplace = True
            self.build_lib = str(Path.cwd())
        else:
            logger.debug("Configuring for regular install")

        project = PyProject(Path())
        config = project.get_hwh_config().cython
        nthreads = config.nthreads
        if _CONFIG_OPTIONS and "nthreads" in _CONFIG_OPTIONS:
            nthreads = _CONFIG_OPTIONS["nthreads"]
            logger.debug("nthreads overridden by command line option")
        logger.debug(f"Using nthreads={nthreads}")
        self.parallel = nthreads

    def run(self):
        """Run the build process."""
        logger.debug(f"Running build_ext (editable={self._is_editable})")
        logger.debug(f"Build lib: {self.build_lib}")
        logger.debug(f"Build temp: {self.build_temp}")

        # Run the actual build
        super().run()

    def _copy_extension_files(self):
        """Copy extension files to their final locations for editable installs."""
        if not self._original_build_lib:
            return

        build_lib_path = Path(self._original_build_lib)
        source_path = Path.cwd()

        logger.debug(f"Copying extension files from {build_lib_path} to {source_path}")

        # Find all built extension files
        for ext in self.extensions:
            # Get the full path to the built extension
            ext_path = self.get_ext_fullpath(ext.name)
            rel_path = Path(ext_path).relative_to(build_lib_path)
            target_path = source_path / rel_path

            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the extension file
            if ext_path.exists():
                shutil.copy2(ext_path, target_path)
                logger.debug(f"Copied {ext_path} to {target_path}")


def _parse_build_settings(config_settings: dict | None = None) -> dict[str, bool | int]:
    """Parse build settings from config_settings dict."""
    if not config_settings:
        return {}

    result = {}
    try:
        if annotate := config_settings.get("annotate"):
            result["annotate"] = annotate.lower() == "true"

        if nthreads := config_settings.get("nthreads"):
            try:
                result["nthreads"] = int(nthreads)
            except ValueError:
                logger.error(f"Invalid nthreads value: {nthreads}")

        if force := config_settings.get("force"):
            result["force"] = force.lower() == "true"

        if config_settings.get("linetrace"):
            result["linetrace"] = True

    except Exception:
        logger.exception("Error parsing config settings")
        return {}

    return result


def _build_extension(
    inplace: bool = False, config_settings={}
) -> dict[str, Any]:
    """Build the extension modules with better editable install handling.

    returns: dict of kwargs for Distribution object
    """

    logger.debug("=== Starting _build_extension ===")
    logger.debug(f"\n with config {config_settings}")

    project = PyProject(Path())
    name = project.package_name

    dist_kwargs = {
        "name": name,
        "version": project.package_version,
        "ext_modules": _get_ext_modules(project, config_settings=config_settings),
        "packages": project.packages,
        "package_data": {pkg: ["*.pxd", "*.so"] for pkg in project.packages},
        "include_package_data": True,
    }

    dist_kwargs["package_dir"] = project.package_dir or project.discovered_package_dir

    dist = Distribution(dist_kwargs)
    dist.has_ext_modules = lambda: True

    cmd = EditableBuildExt(dist)
    cmd.inplace = inplace
    cmd.ensure_finalized()
    cmd.run()

    _EXTENSIONS_BUILT = True
    logger.debug("=== Finished _build_extension ===\n")
    return dist_kwargs


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Build wheel with explicit editable install handling."""

    setup_logging(config_settings)
    logger.info("=== Starting build_wheel ===")

    project = PyProject(Path())

    # Build extensions first, this now handles all the Distribution setup
    dist_kwargs = {
        "entry_points": project.entrypoints,
        "install_requires": [str(d) for d in project.runtime_dependencies],
        "extras_require": project.toml.get("project", {}).get("optional-dependencies", None)
    }
    if not _EXTENSIONS_BUILT:
        dist_kwargs |= _build_extension(
            _is_editable_install(), config_settings=config_settings
        )
    else:
        logger.debug("Extensions already built, skipping")

    from wheel.bdist_wheel import bdist_wheel as wheel_command

    class BdistWheelCommand(wheel_command):
        def finalize_options(self):
            super().finalize_options()
            self.root_is_pure = False
            self.user_options = config_settings

        def run(self):
            logger.debug("Running custom bdist_wheel command")
            super().run()

    # Create distribution using same config from _build_extension
    dist = Distribution(dist_kwargs)
    dist.cmdclass = {"build_ext": EditableBuildExt}
    dist.has_ext_modules = lambda: True

    cmd = BdistWheelCommand(dist)
    cmd.dist_dir = wheel_directory
    cmd.distribution.script_name = "fubar"
    cmd.ensure_finalized()
    logger.debug("Starting wheel build")
    cmd.run()
    logger.debug("Finished wheel build")

    # Find the built wheel
    wheel_path = next(Path(wheel_directory).glob("*.whl"))
    logger.debug(f"Built wheel: {wheel_path}")
    logger.debug("=== Finished build_wheel ===\n")
    return wheel_path.name


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    """Build editable wheel."""

    setup_logging(config_settings)
    logger.debug("=== Starting build_editable ===")
    logger.debug(f"Wheel directory: {wheel_directory}")
    logger.debug(f"Config settings: {config_settings}")
    logger.debug(f"Metadata directory: {metadata_directory}")

    # Editable install=inplace
    logger.debug(f"passing config {config_settings}")
    if not _EXTENSIONS_BUILT:
        _build_extension(inplace=True, config_settings=config_settings)

    logger.debug("Calling setuptools build_editable")
    result = _build_editable(wheel_directory, config_settings, metadata_directory)
    logger.debug(f"Editable build result: {result}")
    logger.debug("=== Finished build_editable ===\n")
    return result


def build_sdist(sdist_directory, config_settings=None):
    """Build source distribution. How is that meant to work with compiled code?"""

    setup_logging(config_settings)
    from setuptools.build_meta import build_sdist as _build_sdist

    return _build_sdist(sdist_directory, config_settings)


def _pyx_paths_from_sources(sources: Sequence[str], package_paths: Sequence[Path]) -> List[Path]:
    logger.debug("Using explicit sources: %s", sources)
    package_paths = set(package_paths)
    pyx_paths = []
    discarded_orphans = []
    discarded_non_pyx = []
    for pyx_path in map(Path, sources):
        if pyx_path.parent not in package_paths:
            discarded_orphans.append(pyx_path)
        elif pyx_path.suffix not in ".pyx":
            discarded_non_pyx.append(pyx_path)
        else:
            pyx_paths.append(pyx_path)

    if discarded_orphans:
        warnings.warn("The following sources were orphaned from packages and have been ignored: "
                        f"{discarded_orphans}")
    if discarded_non_pyx:
        warnings.warn("The following sources will not be cythonised as they are not .pyx files: "
                      f"{discarded_non_pyx}")
    return pyx_paths


def _find_cython_files(package_paths: Sequence[Path]) -> List[Path]:
    """Find all Cython source files in the package directory."""

    def find(pkg_path: Path):
        logger.debug("Searching for Cython files in: %s", pkg_path)
        found_pyx = list(pkg_path.glob("*.pyx"))
        if found_pyx:
            logger.debug("  Found: %s", found_pyx)
        else:
            logger.debug("  None found")
        return found_pyx

    logger.debug("=== finding cython files ===")
    pyx_files = list(chain.from_iterable(
        find(pkg_path) for pkg_path in package_paths))
    logger.debug(f"Found .pyx files: {pyx_files}")
    return pyx_files

def _exclude_extensions(pyx_paths: Sequence[Path], exclude_dirs: Sequence[str]):
    logger.debug("Using exclude dirs: %s", exclude_dirs)
    excluded = []
    included = []
    for pyx_path in pyx_paths:
        for exclude_path in map(Path, exclude_dirs):
            if pyx_path.is_relative_to(exclude_path):
                excluded.append(pyx_path)
            else:
                included.append(pyx_path)
    if excluded:
        logger.debug("Excluded: %s", excluded)
        logger.debug("Kept: %s", included)
    else:
        logger.debug("Nothing excluded")
    return included

def _collect_pyx_paths(
        package_paths: Sequence[Path],
        sources: Sequence[str],
        exclude_dirs: Sequence[str]
):
    pyx_paths = (_pyx_paths_from_sources(sources, package_paths)
                 if sources else
                 _find_cython_files(package_paths))

    if exclude_dirs:
        return _exclude_extensions(pyx_paths, exclude_dirs)
    return pyx_paths
