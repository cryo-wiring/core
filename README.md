# Cryo Wiring Core

JSON Schema validation for cryo-wiring configuration files.

## Installation

```bash
uv add cryo-wiring-core
```

## Usage

```python
import yaml
from cryo_wiring_core import validate_wiring, validate_metadata, validate_components, validate_chip

with open("control.yaml") as f:
    data = yaml.safe_load(f)

validate_wiring(data)        # raises jsonschema.ValidationError on failure

with open("metadata.yaml") as f:
    meta = yaml.safe_load(f)

validate_metadata(meta)      # raises jsonschema.ValidationError on failure

with open("components.yaml") as f:
    comps = yaml.safe_load(f)

validate_components(comps)   # raises jsonschema.ValidationError on failure

with open("chip.yaml") as f:
    chip = yaml.safe_load(f)

validate_chip(chip)          # raises jsonschema.ValidationError on failure
```

## Schemas

This package bundles the JSON Schema files from [cryo-wiring-spec](https://github.com/cryo-wiring/spec) via git submodule:

| Schema                   | Function                | Validates                                            |
| ------------------------ | ----------------------- | ---------------------------------------------------- |
| `wiring.schema.json`     | `validate_wiring()`     | control.yaml, readout_send.yaml, readout_return.yaml |
| `metadata.schema.json`   | `validate_metadata()`   | metadata.yaml                                        |
| `components.schema.json` | `validate_components()` | components.yaml                                      |
| `chip.schema.json`       | `validate_chip()`       | chip.yaml                                            |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and development workflow.
