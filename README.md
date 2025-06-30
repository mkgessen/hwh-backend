# Halfway House backend

[![Tests Passing](https://github.com/mkgessen/hwh-backend/actions/workflows/test-only.yml/badge.svg)](https://github.com/mkgessen/hwh-backend/actions/workflows/test-only.yml)

Provides [PEP-517](https://peps.python.org/pep-0517/) build hooks for building
Cython extensions with setuptools. Currently supports Cython 0.29.

Ideally similar functionality would be provided an actual setuptools backend.

## Requirements

- Python 3.11
- Cython 0.29.xx
- Linux

## Features

- PEP-517 compliant build backend for Cython extensions
- Supports both regular and editable installs
- Configurable through pyproject.toml
- Support for flat and src layouts
- Package discovery using setuptools.find_packages
- Integration with numpy headers (optional)
- Cython compiler directive configuration
- Multi-threading support (complicated way of saying the `nthreads` is
  supported)
- Site-packages configuration options

## Intended use

HWH is intended to be bolt on replacement for projects that build Cython
extensions with setuptools. You should be able to get rid of your `setup.py` and
you don't need to call `python -m setup.py` to build extensions.

HWH backend is mainly configured through optional [[tool.hwh]] section of
`pyproject.toml`.

In addition to [[tool.hwh]] section, HWH emulates
`tool.setuptools.package.find`, so to support src layout and cases where package
directory name != project name in case of flat layout.

This feature is likely to be changed to [[tool.hwh.setuptools.]] in the near
future, but this is the starting point.

### Scenarios that HWH tries to solve

1. Project that has `.pyx` files, but doesn't is not designed to be used by
   other projects. Doesn't contain `.pxd` files
2. Project that has `.pyx` and `.pxd` files and plain `.py` files
3. Project that has .`pyx` and `.pxd` files and depends on another project that
   looks like #2
   - dependency used in both Cython and Python

### `[tool.hwh.cython]`

Core Cython build configuration:

- `language`: Extension language ("c" or "c++"). Defaults to "c"
- `annotate`: Generate Cython annotation HTML files (default: false)
- `nthreads`: Number of parallel compilation threads (default: CPU count)
- `force`: Force rebuild of extensions (default: false)
- `use_numpy_include`: Include numpy headers in compilation (default: false)

### `[tool.hwh.cython.modules]`

Extension module configuration:

- `sources`: List of .pyx files to compile (default: auto-discover)
- `exclude_dirs`: Directories to exclude from auto-discovery
- `include_dirs`: Header search paths
- `library_dirs`: Library search paths
- `libraries`: Libraries to link against
- `extra_compile_args`: Additional compilation arguments
- `extra_link_args`: Additional linker arguments
- `runtime_library_dirs`: Runtime library search paths

Site-packages configuration via `site_packages`:

- `"purelib"`: Use sysconfig.get_path("purelib")
- `"user"`: Use site.getusersitepackages()
- `"site"`: Use site.getsitepackages()
- `"none"`: No automatic site-packages paths

### `[tool.hwh.cython.compiler_directives]`

Cython compiler directives configuration:

```toml
[tool.hwh.cython.compiler_directives]
binding = false            # Generate Python wrapper functions
boundscheck = false        # Array bounds checking
wraparound = false        # Negative indexing
initializedcheck = false  # Check if extension types are initialized
nonecheck = false         # Check for null Python references
overflowcheck = false     # Check for C integer overflows
embedsignature = false    # Include docstrings in the C code
cdivision = false        # Division by zero checking
cdivision_warnings = false # Division by zero warning
profile = false          # Enable profiling
linetrace = false        # Enable line tracing
infer_types = null       # Type inference
type_version_tag = true  # Enable CPython's type attribute cache
```

For more information, see
[Cython docs](https://cython.readthedocs.io/en/0.29.x/src/userguide/source_files_and_compilation.html)
and
[Setup tools extension docs](https://setuptools.pypa.io/en/latest/userguide/ext_modules.html)

## Usage

**Build Configuration**

Build settings can be controlled via command line. Note the different syntax
between `python -m build` (plural --config-settings) and `pip` (singular
--config-setting). Consistency here is great :heart:

The following options are supported:

```shell
# Using python -m build
python -m build --wheel --no-isolation \
    --config-settings annotate=true \
    --config-settings nthreads=4 \
    --config-settings force=true \
    --config-settings linetrace=true

# Using pip
pip install -e . \
    --config-setting annotate=true \
    --config-setting nthreads=4 \
    --config-setting force=true \
    --config-setting linetrace=true
```

## Logging

```shell
pip install --config-setting verbose=debug  # Options: debub, info, warning
```

### `[tool.hwh.cython.compiler_directives]`

HWH exposes the most of Cython's compiler directives. See
[compiler directives](https://cython.readthedocs.io/en/0.29.x/src/userguide/source_files_and_compilation.html#compiler-directives)

### Example `pyproject.toml`

```toml pyproject.toml
[build-system]
requires = ["hwh-backend", "Cython<3.0.0"]
build-backend = "hwh_backend.build"

[project]
name = "mylib"
version = "1.0.0"

[tool.hwh.cython]
language = "c++"
annotate = true
nthreads = 4
force = false
use_numpy_include = true

[tool.hwh.cython.modules]
sources = ["src/mylib/*.pyx"]
exclude_dirs = ["tests", "build"]
include_dirs = ["include"]
library_dirs = ["/usr/local/lib"]
libraries = ["mylib"]
extra_compile_args = ["-O3"]
runtime_library_dirs = ["/usr/local/lib"]
site_packages = "purelib"

[tool.hwh.cython.compiler_directives]
boundscheck = false
wraparound = false
cdivision = true
```
