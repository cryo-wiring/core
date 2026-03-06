# Cryo Wiring Core

Python library for dilution refrigerator wiring configuration — data models, validation, diagram generation, and programmatic building.

## Related Repositories

| Repository                                                      | Description                          |
| --------------------------------------------------------------- | ------------------------------------ |
| [cryo-wiring/spec](https://github.com/cryo-wiring/spec)         | YAML format specification & schemas  |
| [cryo-wiring/cli](https://github.com/cryo-wiring/cli)           | CLI tool                             |
| [cryo-wiring/app](https://github.com/cryo-wiring/app)           | Web UI (FastAPI + Next.js)           |
| [cryo-wiring/template](https://github.com/cryo-wiring/template) | Data repository template             |

## Installation

```bash
pip install cryo-wiring-core
```

## Features

| Module      | Description                                                |
| ----------- | ---------------------------------------------------------- |
| `models`    | Pydantic v2 models (Stage, Component types, WiringConfig)  |
| `validate`  | JSON Schema validation against cryo-wiring-spec            |
| `loader`    | YAML loading, module expansion, component catalog          |
| `builder`   | Programmatic cooldown generation from Python code          |
| `summary`   | Wiring summary tables (terminal, Markdown, HTML)           |
| `diagram`   | Publication-quality wiring diagrams (matplotlib)           |

## Quick Start

### Load & inspect a cooldown

```python
from cryo_wiring_core import load_cooldown, print_summary, generate_diagram

metadata, control, readout_send, readout_return = load_cooldown("path/to/cooldown")

# Rich terminal table
print_summary(control, readout_send, readout_return)

# Publication-quality SVG
generate_diagram(control, readout_send, readout_return, output="wiring.svg")
```

### Build a cooldown from component models

```python
from cryo_wiring_core import (
    CooldownBuilder, Attenuator, Filter, Isolator, Amplifier, CustomComponent, Stage,
    print_summary, generate_diagram,
)

b = CooldownBuilder(num_qubits=16)

b.control_module("ctrl", {
    Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
    Stage.K4:  [Attenuator(model="XMA-2082-6431-20", value_dB=20)],
    Stage.MXC: [
        Attenuator(model="XMA-2082-6431-20", value_dB=20),
        Filter(model="XMA-EF-03", filter_type="Eccosorb"),
    ],
})

b.readout_send_module("rs", {
    Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
    Stage.K4:  [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
})

b.readout_return_module("rr", {
    Stage.CP:  [Isolator(model="LNF-ISC4_12A"), Isolator(model="LNF-ISC4_12A")],
    Stage.K50: [Amplifier(model="LNF-LNC03_14A", amplifier_type="HEMT", gain_dB=40)],
    Stage.RT:  [Amplifier(model="MITEQ-AFS3", amplifier_type="RT", gain_dB=20)],
})

# Get WiringConfig objects for analysis
control, readout_send, readout_return = b.build()
print_summary(control, readout_send, readout_return)
generate_diagram(control, readout_send, readout_return, output="wiring.svg")

# Or write YAML files to a directory
b.write("anemone/current", fridge="anemone", chip_name="sample-chip")
```

### Template-based generation

```python
from cryo_wiring_core import build_cooldown

build_cooldown(
    output_dir="anemone/current",
    fridge="anemone",
    chip_name="sample-chip",
    num_qubits=16,
)
```

### Validate YAML files

```python
from cryo_wiring_core import validate_wiring, validate_metadata
import yaml

with open("control.yaml") as f:
    data = yaml.safe_load(f)

validate_wiring(data)      # raises jsonschema.ValidationError on failure
validate_metadata(meta)
```

## Component Types

| Class             | Fields                              | Diagram Label    | Example                                              |
| ----------------- | ----------------------------------- | ---------------- | ---------------------------------------------------- |
| `Attenuator`      | `value_dB`                          | `10 dB`          | `Attenuator(model="XMA-10dB", value_dB=10)`          |
| `Filter`          | `filter_type`                       | `Lowpa` / `FLT`  | `Filter(model="K&L", filter_type="Lowpass")`          |
| `Isolator`        | —                                   | `ISO`            | `Isolator(model="LNF-ISC4_12A")`                     |
| `Amplifier`       | `amplifier_type`, `gain_dB`         | `+40 dB`         | `Amplifier(model="HEMT", gain_dB=40)`                |
| `CustomComponent` | `custom_type`                       | user-defined     | `CustomComponent(model="BLK-18", custom_type="DC block")` |

All components share `model` and `serial` fields, and expose `label`, `summary_label`, `attenuation`, `gain` properties.

## Schemas

This package bundles JSON Schema files from [cryo-wiring-spec](https://github.com/cryo-wiring/spec):

| Schema                   | Function                | Validates                                            |
| ------------------------ | ----------------------- | ---------------------------------------------------- |
| `wiring.schema.json`     | `validate_wiring()`     | control.yaml, readout_send.yaml, readout_return.yaml |
| `metadata.schema.json`   | `validate_metadata()`   | metadata.yaml                                        |
| `components.schema.json` | `validate_components()` | components.yaml                                      |
| `chip.schema.json`       | `validate_chip()`       | chip.yaml                                            |

## Documentation

Full documentation is available at **[cryo-wiring.github.io/core](https://cryo-wiring.github.io/core/)**.

## Examples

Interactive [marimo](https://marimo.io/) notebooks are available in the `examples/` directory.

```bash
uv sync --group example
uv run marimo edit examples/getting_started.py
```

The notebook covers builder usage, summary tables, SVG diagram rendering, and component add/remove/replace operations.

Try it online in the [Playground](https://cryo-wiring.github.io/core/playground/) — no installation required.

## Development

```bash
uv sync
uv run pytest
```
