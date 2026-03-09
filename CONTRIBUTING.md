# Contributing

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
git clone --recurse-submodules https://github.com/cryowire/core.git
cd core
uv sync
```

If you already cloned without `--recurse-submodules`:

```bash
git submodule update --init
```

## Project Structure

```
core/
├── spec/                           # git submodule (cryowire/spec)
│   └── schema/                     # canonical JSON Schema files
├── src/cryowire/
│   ├── __init__.py                 # public API exports
│   ├── validate.py                 # validation functions
│   └── schemas/                    # bundled schemas (copied from spec/)
├── tests/
│   └── test_validate.py
├── Makefile
├── pyproject.toml
└── .github/workflows/ci.yml
```

## Common Tasks

### Run tests

```bash
make test
# or directly:
uv run pytest tests/ -v
```

### Sync schemas from spec submodule

When `cryowire/spec` is updated:

```bash
git submodule update --remote spec   # pull latest spec
make sync-schemas                     # copy schemas to source
make test                             # verify nothing broke
```

### Check schema drift

```bash
make check-schemas
```

CI runs this automatically on every push/PR to catch schema drift.

### Add a new schema

1. Schema is added to `cryowire/spec` first (source of truth)
2. Update the spec submodule: `git submodule update --remote spec`
3. Run `make sync-schemas`
4. Add a `validate_<name>()` function in `validate.py`
5. Export it from `__init__.py`
6. Add tests in `test_validate.py`

## Public API

| Function | Schema | Validates |
|----------|--------|-----------|
| `validate_wiring(data)` | `wiring.schema.json` | control.yaml, readout_send.yaml, readout_return.yaml |
| `validate_metadata(data)` | `metadata.schema.json` | metadata.yaml |
| `validate_components(data)` | `components.schema.json` | components.yaml |
| `validate_chip(data)` | `chip.schema.json` | chip.yaml |

All functions raise `jsonschema.ValidationError` on failure, return `None` on success.

## Release

Releases are published to PyPI automatically via GitHub Actions using [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC).

### Steps

1. Update `version` in `pyproject.toml`
2. Commit and push to `main`
3. Create and push a git tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `publish.yml` workflow will:
1. Run tests and schema sync check
2. Build sdist + wheel
3. Publish to PyPI via OIDC (no API token needed)

### PyPI Setup (one-time)

On [pypi.org](https://pypi.org):

1. Go to your project settings (or create the project on first publish)
2. **Publishing** > **Add a new publisher**
3. Set:
   - Owner: `cryowire`
   - Repository: `core`
   - Workflow: `publish.yml`
   - Environment: `pypi`
4. On GitHub, create an environment named `pypi` in the repo settings

## CI

GitHub Actions workflows:

**`ci.yml`** — runs on push/PR to `main`:
1. Checkout with submodules
2. `make check-schemas` — fails if bundled schemas diverge from spec submodule
3. `make test` — runs pytest

**`publish.yml`** — runs on `v*` tags:
1. Test + schema sync check
2. Build sdist and wheel
3. Publish to PyPI via Trusted Publishing
