<p align="center"><a href="https://github.com/cryowire">
  <img src="https://raw.githubusercontent.com/cryowire/artwork/main/logo-type/logotype.png" alt="cryowire" width="600" />
</a></p>

<h1 align="center">cryowire</h1>
<p align="center">Python library for dilution refrigerator wiring configuration — data models, validation, diagram generation, and programmatic building.</p>
<p align="center">
  <a href="https://cryowire.github.io/"><img src="https://img.shields.io/badge/Website-cryowire.github.io-38bdf8?style=for-the-badge" alt="Website" /></a>
  <a href="https://cryowire.github.io/cryowire/"><img src="https://img.shields.io/badge/Docs-API_Reference-818cf8?style=for-the-badge" alt="Docs" /></a>
</p>

## Installation

```bash
pip install cryowire
```

## Features

| Module      | Description                                                |
| ----------- | ---------------------------------------------------------- |
| `models`    | Pydantic v2 models (Stage, Component types, WiringConfig)  |
| `validate`  | JSON Schema validation against cryowire-spec            |
| `loader`    | YAML loading, module expansion, component catalog          |
| `builder`   | Programmatic cooldown generation from Python code          |
| `summary`   | Wiring summary tables (terminal, Markdown, HTML)           |
| `diagram`   | Publication-quality wiring diagrams (matplotlib)           |

## Quick Start

### Build a cooldown

```python
from cryowire import (
    Amplifier, Attenuator, ChipConfig, CooldownBuilder,
    CooldownMetadata, Filter, Isolator, Stage,
)

# 1. Component catalog
catalog = {
    "XMA-10dB": Attenuator(model="XMA-2082-6431-10", value_dB=10),
    "XMA-20dB": Attenuator(model="XMA-2082-6431-20", value_dB=20),
    "Eccosorb": Filter(model="XMA-EF-03", filter_type="Eccosorb"),
    "K&L-LPF": Filter(model="K&L-5VLF", filter_type="Lowpass"),
    "RT-AMP": Amplifier(model="MITEQ-AFS3", amplifier_type="RT", gain_dB=20),
    "LNF-HEMT": Amplifier(model="LNF-LNC03_14A", amplifier_type="HEMT", gain_dB=40),
    "LNF-ISO": Isolator(model="LNF-ISC4_12A"),
}

# 2. Build cooldown (reference components by key)
cooldown = (
    CooldownBuilder(
        chip=ChipConfig(name="sample-8q", num_qubits=8, qubits_per_readout_line=4),
        metadata=CooldownMetadata(cryo="your-cryo", cooldown_id="cd001", date="2026-03-06"),
        catalog=catalog,
        control={
            Stage.K50: ["XMA-10dB"],
            Stage.K4: ["XMA-20dB"],
            Stage.MXC: ["XMA-20dB", "Eccosorb"],
        },
        readout_send={Stage.K50: ["XMA-10dB"], Stage.K4: ["XMA-10dB"]},
        readout_return={
            Stage.RT: ["RT-AMP"],
            Stage.K50: ["LNF-HEMT"],
            Stage.CP: ["LNF-ISO", "LNF-ISO"],
        },
    )
    .add("C00", Stage.STILL, "K&L-LPF")
    .remove("RR00", Stage.CP, index=1)
    .build()
)

# 3. Per-line overrides (context manager)
with cooldown.for_lines("C03", "C05") as lines:
    lines.remove(Stage.MXC, component_type=Filter)
    lines.replace(Stage.K4, 0, "XMA-10dB")

# Summary (terminal / markdown / html)
cooldown.summary()
md = cooldown.summary(fmt="markdown")

# Publication-quality SVG diagram
cooldown.diagram(output="wiring.svg", representative=True)

# Export YAML files
cooldown.write("output/")
```

### Load & inspect an existing cooldown

```python
from cryowire import load_cooldown, print_summary, generate_diagram

metadata, control, readout_send, readout_return = load_cooldown("path/to/cooldown")

print_summary(control, readout_send, readout_return)
generate_diagram(control, readout_send, readout_return, output="wiring.svg")
```

### Template-based generation

```python
from cryowire import build_cooldown

build_cooldown(
    output_dir="your-cryo/2026/cd001",
    cryo="your-cryo",
    chip_name="sample-chip",
    num_qubits=16,
)
```

### Validate YAML files

```python
from cryowire import validate_wiring, validate_metadata
import yaml

with open("control.yaml") as f:
    data = yaml.safe_load(f)

validate_wiring(data)      # raises jsonschema.ValidationError on failure
validate_metadata(meta)
```

## Component Types

| Class             | Fields                              | Diagram Label    | Example                                              |
| ----------------- | ----------------------------------- | ---------------- | ---------------------------------------------------- |
| `Attenuator` | `value_dB`                  | `10 dB`         | `Attenuator(model="XMA-10dB", value_dB=10)` |
| `Filter`     | `filter_type`               | `Lowpass` / `FLT` | `Filter(model="K&L", filter_type="Lowpass")` |
| `Isolator`   | —                           | `ISO`           | `Isolator(model="LNF-ISC4_12A")`            |
| `Amplifier`  | `amplifier_type`, `gain_dB` | `+40 dB`        | `Amplifier(model="HEMT", gain_dB=40)`        |

All components share `model` and `serial` fields, and expose `label`, `summary_label`, `attenuation`, `gain` properties.

## Schemas

This package bundles JSON Schema files from [cryowire-spec](https://github.com/cryowire/spec):

| Schema                   | Function                | Validates                                            |
| ------------------------ | ----------------------- | ---------------------------------------------------- |
| `wiring.schema.json`     | `validate_wiring()`     | control.yaml, readout_send.yaml, readout_return.yaml |
| `metadata.schema.json`   | `validate_metadata()`   | metadata.yaml                                        |
| `components.schema.json` | `validate_components()` | components.yaml                                      |
| `chip.schema.json`       | `validate_chip()`       | chip.yaml                                            |

## Documentation

Full documentation is available at **[cryowire.github.io/cryowire](https://cryowire.github.io/cryowire/)**.

## Examples

A Jupyter notebook tutorial is available in the `examples/notebooks/` directory.

```bash
pip install cryowire jupyter
jupyter notebook examples/notebooks/tutorial.ipynb
```

The notebook covers builder usage, summary tables, SVG diagram rendering, and component add/remove/replace operations.

Try it online in the [Playground](https://cryowire.github.io/cryowire/playground/) — no installation required.

## Development

```bash
uv sync
uv run pytest
```
