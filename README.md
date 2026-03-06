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

### Build a cooldown with method chaining

```python
from cryo_wiring_core import (
    Amplifier, Attenuator, CooldownBuilder, Filter, Isolator, Stage,
)

cooldown = (
    CooldownBuilder(num_qubits=8)
    .control_module("ctrl", {
        Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
        Stage.K4: [Attenuator(model="XMA-2082-6431-20", value_dB=20)],
        Stage.MXC: [
            Attenuator(model="XMA-2082-6431-20", value_dB=20),
            Filter(model="XMA-EF-03", filter_type="Eccosorb"),
        ],
    })
    .readout_send_module("rs", {
        Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
        Stage.K4: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
    })
    .readout_return_module("rr", {
        Stage.RT: [Amplifier(model="MITEQ-AFS3", amplifier_type="RT", gain_dB=20)],
        Stage.K50: [Amplifier(model="LNF-LNC03_14A", amplifier_type="HEMT", gain_dB=40)],
        Stage.CP: [Isolator(model="LNF-ISC4_12A"), Isolator(model="LNF-ISC4_12A")],
    })
    # Per-line overrides
    .add("C00", Stage.STILL, Filter(model="K&L-5VLF", filter_type="Lowpass"))
    .for_lines("C03", "C05")
        .remove(Stage.MXC, component_type="filter")
        .replace(Stage.K4, 0, Attenuator(model="XMA-2082-6431-10", value_dB=10))
    .end()
    .build()
)

# Summary (terminal / markdown / html)
cooldown.summary()
md = cooldown.summary(fmt="markdown")

# Publication-quality SVG diagram
cooldown.diagram(output="wiring.svg", representative=True)

# Export YAML files
cooldown.write("output/", fridge="your-cryo", chip_name="sample-8q")
```

### Load & inspect an existing cooldown

```python
from cryo_wiring_core import load_cooldown, print_summary, generate_diagram

metadata, control, readout_send, readout_return = load_cooldown("path/to/cooldown")

print_summary(control, readout_send, readout_return)
generate_diagram(control, readout_send, readout_return, output="wiring.svg")
```

### Template-based generation

```python
from cryo_wiring_core import build_cooldown

build_cooldown(
    output_dir="your-cryo/current",
    fridge="your-cryo",
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

Try it online in the [Playground](https://cryo-wiring.github.io/core/marimo/) — no installation required.

## Development

```bash
uv sync
uv run pytest
```
