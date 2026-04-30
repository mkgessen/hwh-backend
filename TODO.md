# Python 3.12/3.13 Compatibility TODO

## Issues Identified

### 1. `wheel` Internal API Misuse (High — `build.py:370-392`)

Two problems in `BdistWheelCommand`:

- **`self.user_options = config_settings` (line 376)**: `user_options` in distutils commands
  is a class-level list of `(long, short, desc)` tuples used for CLI option parsing. Assigning
  a settings dict here is incorrect and could break with newer wheel versions.
- **`cmd.distribution.script_name = "fubar"` (line 389)**: A distutils internal hack to
  silence an error. The value "fubar" is meaningless but the assignment is necessary —
  `Distribution()` leaves `script_name=None` when constructed programmatically, and
  distutils `build_py` calls `os.path.abspath(script_name)` which fails on None.
  Fixed by using the conventional `"setup.py"` string instead.

### 2. `pyproject_metadata` API Drift (High — `parser.py:62`)

`StandardMetadata.from_pyproject(self.toml)` — in `pyproject-metadata>=0.8.0` the signature
changed. Unrecognised keys in `pyproject.toml` now raise by default unless
`allow_extra_keys=True` is passed. The minimum pinned version is `>=0.7.0`, so this can break
silently on dependency update.

### 3. `setuptools` Version Floor for Python 3.12 (Medium — `pyproject.toml:2,27`)

`distutils` was removed from the Python 3.12 stdlib. setuptools bundles its own distutils
shim, but `setuptools>=68.0` is the bare minimum. `setuptools>=69.0` is recommended for
reliable 3.12 support.

### 4. `packaging` Undeclared Dependency (Low — `parser.py:10-11`)

`from packaging.requirements import Requirement` and `from packaging.version import Version`
are used but `packaging` is not listed in `pyproject.toml` dependencies. Currently available
transitively via setuptools/pip but should be declared explicitly.

### 5. `numpy` Hard Dependency (Low — `pyproject.toml:30`)

`numpy>=2.0.0` is a required runtime dependency, but numpy is only needed when
`use_numpy_include = true`. Forces numpy on every consumer of hwh-backend unnecessarily.
Should be an optional dependency.

### 6. Tooling Targets Hardcoded to 3.11 (Low — `pyproject.toml:62,72,89`)

`target-version = "py311"` in `[tool.black]` and `[tool.ruff]`, and `python_version = "3.11"`
in `[tool.mypy]`. Needs updating when 3.12+ support lands.

---

## Solutions

### Fix 1: `wheel` Internal API — Replace `BdistWheelCommand` subclass

The `BdistWheelCommand` subclass overrides `finalize_options` and `run` but abuses internal
attributes. The goal is: force `root_is_pure = False` so the wheel is tagged as non-pure.

**Plan:**
- Remove the override of `self.user_options` entirely — it serves no purpose here.
  `config_settings` are already parsed upstream by `_parse_build_settings`.
- Replace `cmd.distribution.script_name = "fubar"` with the correct setuptools approach:
  set `Distribution.metadata.name` directly, or use `dist.script_name` only if required by
  the installed version of setuptools (check via `hasattr`).
- Alternatively, avoid subclassing `bdist_wheel` entirely and configure the command via
  `dist.command_options` dict, which is the stable public API.

**Minimal safe fix:**
```python
class BdistWheelCommand(wheel_command):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False
    # Remove run() override — it only calls super().run()
```
And replace `cmd.distribution.script_name = "fubar"` with the distribution being constructed
with a proper `name` already set (which it is via `dist_kwargs["name"]`). The `script_name`
hack may only be needed for older setuptools; test whether it can simply be removed.

### Fix 2: `pyproject_metadata` API — Pin version and pass `allow_extra_keys`

**Plan:**
- Bump minimum version pin to `pyproject-metadata>=0.8.0` in `pyproject.toml`.
- Update the call in `parser.py:62`:
  ```python
  StandardMetadata.from_pyproject(self.toml, allow_extra_keys=True)
  ```
  `allow_extra_keys=True` is needed because `pyproject.toml` will contain `[tool.hwh]`
  and other non-standard sections that `pyproject-metadata` doesn't know about.
- Verify behaviour with a test that includes `[tool.hwh]` keys in a fixture pyproject.toml.

### Fix 3: `setuptools` Version Floor

**Plan:**
- Bump both occurrences in `pyproject.toml` from `>=68.0` to `>=69.0`:
  - `build-system.requires` (line 2)
  - `project.dependencies` (line 27)
- `setuptools>=69.0` ensures the bundled distutils shim fully covers the removed stdlib
  `distutils` in Python 3.12.
- Also add `"Programming Language :: Python :: 3.12"` to classifiers once validated.
