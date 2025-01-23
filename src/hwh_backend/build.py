from pathlib import Path
from typing import List, Optional, Union

from Cython.Build import cythonize
from setuptools.build_meta import (
    build_editable as _build_editable,
)
from setuptools.command.build_ext import build_ext
from setuptools.dist import Distribution
from setuptools.extension import Extension

from .parser import PyProject

# Global flag to prevent double builds
_EXTENSIONS_BUILT = False


def debug_print(*args, **kwargs):
    """Helper function for debug output"""
    print("[DEBUG]", *args, **kwargs)


def find_cython_files(
    source_dir: Path,
    sources: Optional[List[Union[str, Path]]] = None,
    exclude_dirs: Optional[List[str]] = None,
) -> List[Path]:
    """Find all Cython source files in the package directory."""
    debug_print(f"Searching for Cython files in: {source_dir}")
    debug_print(f"Explicit sources: {sources}")
    debug_print(f"Exclude dirs: {exclude_dirs}")

    if sources:
        # Convert all sources to Path objects relative to source_dir
        res = [
            source_dir / src if isinstance(src, str) else src
            for src in sources
            if str(src).endswith(".pyx")
        ]
        debug_print(f"Using explicit sources: {res}")
        return res

    all_pyx = list(source_dir.rglob("*.pyx"))
    debug_print(f"Found all .pyx files: {all_pyx}")

    # Filter out all directories that are excluded
    exclude_dirs = set(exclude_dirs or [])
    if exclude_dirs:
        # Convert exclude_dirs to full paths relative to source_dir
        exclude_paths = {source_dir / excluded for excluded in exclude_dirs}
        debug_print(f"Exclude paths: {exclude_paths}")
        filtered = [
            pyx
            for pyx in all_pyx
            if not any(exclude_path in pyx.parents for exclude_path in exclude_paths)
        ]
        debug_print(f"After exclusion: {filtered}")
        return filtered

    return list(all_pyx)


def _get_ext_modules(project: PyProject):
    """Get Cython extension modules configuration."""
    debug_print("\n=== Starting _get_ext_modules ===")
    debug_print(f"Project name: {project.package_name}")
    debug_print(f"Project version: {project.package_version}")

    import site

    site_packages = [site.getsitepackages()[0]]
    debug_print(f"Site packages: {site_packages}")

    # Create directory lists for Extension ctor and cythonize()
    config = project.get_hwh_config().cython
    library_dirs = config.library_dirs + site_packages
    runtime_library_dirs = config.runtime_library_dirs + site_packages
    include_dirs = config.include_dirs + site_packages

    debug_print(f"Library dirs: {library_dirs}")
    debug_print(f"Runtime library dirs: {runtime_library_dirs}")
    debug_print(f"Include dirs: {include_dirs}")

    # Find all .pyx files in the package directory
    package_dir = Path(project.package_name)
    debug_print(f"Looking for .pyx files in package dir: {package_dir}")

    pyx_files = find_cython_files(
        package_dir, sources=config.sources, exclude_dirs=config.exclude_dirs
    )
    debug_print(f"Found .pyx files: {pyx_files}")

    # Create Extensions
    ext_modules = []
    for pyx_file in pyx_files:
        # Convert path to proper module path
        rel_path = pyx_file.relative_to(package_dir)
        debug_print(f"\nProcessing: {pyx_file}")
        debug_print(f"Relative path: {rel_path}")

        # Construct full module path including package name
        module_parts = [project.package_name] + [
            part for part in rel_path.parent.parts if part != "."
        ]
        if rel_path.name != "__init__.pyx":
            module_parts.append(rel_path.stem)

        module_path = ".".join(module_parts)
        debug_print(f"Constructed module path: {module_path}")

        ext = Extension(
            module_path,
            [str(pyx_file)],
            language=config.language,
            library_dirs=library_dirs,
            runtime_library_dirs=runtime_library_dirs,
        )
        debug_print(f"Created Extension object: {ext.name}")
        ext_modules.append(ext)

    debug_print(f"\nTotal extensions to build: {len(ext_modules)}")
    debug_print("=== Finished _get_ext_modules ===\n")

    return cythonize(
        ext_modules,
        nthreads=config.nthreads,
        force=config.force,
        annotate=config.annotate,
        compiler_directives=config.compiler_directives.as_dict(),
        include_path=include_dirs,  # This helps find .pxd files
    )


def _build_extension():
    """Build the extension modules."""
    debug_print("\n=== Starting _build_extension ===")
    global _EXTENSIONS_BUILT

    if _EXTENSIONS_BUILT:
        debug_print("Extensions already built, skipping")
        return

    debug_print("Building extensions for the first time")
    project = PyProject(Path())
    name = project.package_name
    debug_print(f"Package name: {name}")

    dist = Distribution({"name": name, "ext_modules": _get_ext_modules(project)})
    dist.has_ext_modules = lambda: True

    cmd = build_ext(dist)
    cmd.ensure_finalized()
    debug_print("Starting build_ext.run()")
    cmd.run()
    debug_print("Finished build_ext.run()")

    # Copy built extensions to source directory
    built_files = cmd.get_outputs()
    debug_print(f"Built files: {built_files}")

    # for output in built_files:
    #     if os.path.exists(output):
    #         filename = os.path.basename(output)
    #         target_dir = Path(name)
    #         target_path = target_dir / filename
    #         debug_print(f"Copying {output} to {target_path}")
    #         shutil.copy2(output, target_path)
    #
    _EXTENSIONS_BUILT = True
    debug_print("=== Finished _build_extension ===\n")


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Build wheel."""
    debug_print("\n=== Starting build_wheel ===")
    debug_print(f"Wheel directory: {wheel_directory}")
    debug_print(f"Config settings: {config_settings}")
    debug_print(f"Metadata directory: {metadata_directory}")

    _build_extension()

    project = PyProject(Path())
    name = project.package_name
    debug_print(f"Building wheel for {name} version {project.package_version}")

    # Configure the distribution
    dist = Distribution(
        {
            "name": name,
            "version": str(project.package_version),
            "ext_modules": _get_ext_modules(project),
            "packages": [name],
            "package_data": {
                name: ["*.pxd", "*.so"],
            },
            "include_package_data": True,
        }
    )

    dist.script_name = "youcanapparentlyputanythinghere"
    dist.has_ext_modules = lambda: True

    from wheel.bdist_wheel import bdist_wheel as wheel_command

    class BdistWheelCommand(wheel_command):
        def finalize_options(self):
            super().finalize_options()
            self.root_is_pure = False

        def run(self):
            debug_print("Running custom bdist_wheel command")
            super().run()

    cmd = BdistWheelCommand(dist)
    cmd.dist_dir = wheel_directory

    cmd.ensure_finalized()
    debug_print("Starting wheel build")
    cmd.run()
    debug_print("Finished wheel build")

    # Find the built wheel
    wheel_path = next(Path(wheel_directory).glob("*.whl"))
    debug_print(f"Built wheel: {wheel_path}")
    debug_print("=== Finished build_wheel ===\n")
    return wheel_path.name


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    """Build editable wheel."""
    debug_print("\n=== Starting build_editable ===")
    debug_print(f"Wheel directory: {wheel_directory}")
    debug_print(f"Config settings: {config_settings}")
    debug_print(f"Metadata directory: {metadata_directory}")

    _build_extension()

    debug_print("Calling setuptools build_editable")
    result = _build_editable(wheel_directory, config_settings, metadata_directory)
    debug_print(f"Editable build result: {result}")
    debug_print("=== Finished build_editable ===\n")
    return result
