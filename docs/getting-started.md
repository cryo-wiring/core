# Getting Started

## Installation

```bash
pip install cryowire
```

## CLI Workflow

### Initialize a data project

```bash
cryowire init ./my-data
cd my-data
```

This generates `.cryowire.yaml`, `components.yaml`, and `templates/`. Edit these to match your lab's components and standard wiring modules.

### Create, edit, and build

```bash
cryowire new my-cryo --qubits 8          # create cooldown from templates
vi my-cryo/2026/cd001/control.yaml        # edit wiring
cryowire build my-cryo/2026/cd001/        # generate cooldown.yaml, SVG, README
cryowire validate my-cryo/2026/cd001/     # validate against schema
```

## Python API

## Build a cooldown configuration

`CooldownBuilder` supports full method chaining.
Define modules, apply per-line overrides, and call `.build()` in a single expression.

```python
from cryowire import (
    Amplifier,
    Attenuator,
    CooldownBuilder,
    Filter,
    Isolator,
    Stage,
)

cooldown = (
    CooldownBuilder(num_qubits=8)
    .control_module(
        "ctrl",
        {
            Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
            Stage.K4: [Attenuator(model="XMA-2082-6431-20", value_dB=20)],
            Stage.MXC: [
                Attenuator(model="XMA-2082-6431-20", value_dB=20),
                Filter(model="XMA-EF-03", filter_type="Eccosorb"),
            ],
        },
    )
    .readout_send_module(
        "rs",
        {
            Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
            Stage.K4: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
        },
    )
    .readout_return_module(
        "rr",
        {
            Stage.RT: [Amplifier(model="MITEQ-AFS3", amplifier_type="RT", gain_dB=20)],
            Stage.K50: [Amplifier(model="LNF-LNC03_14A", amplifier_type="HEMT", gain_dB=40)],
            Stage.CP: [Isolator(model="LNF-ISC4_12A"), Isolator(model="LNF-ISC4_12A")],
        },
    )
    .build()
)
```

## Per-line overrides

Add, remove, or replace components on individual lines:

```python
cooldown = (
    CooldownBuilder(num_qubits=8)
    .control_module("ctrl", { ... })
    # Add a filter at Still on C00
    .add("C00", Stage.STILL, Filter(model="K&L-5VLF", filter_type="Lowpass"))
    # Bulk override on C03 and C05
    .for_lines("C03", "C05")
        .remove(Stage.MXC, component_type="filter")
        .replace(Stage.K4, 0, Attenuator(model="XMA-2082-6431-10", value_dB=10))
    .end()
    .build()
)
```

## Wiring summary

```python
# Rich terminal output
cooldown.summary()

# Markdown string
md = cooldown.summary(fmt="markdown")

# HTML string
html = cooldown.summary(fmt="html")
```

## Wiring diagram

```python
# Save as SVG (default)
cooldown.diagram(output="wiring.svg", representative=True)

# Save as PDF
cooldown.diagram(output="wiring.pdf")
```

## Export YAML files

```python
cooldown.write("output/", cryo="your-cryo", chip_name="sample-8q")
```

This creates a directory following the [cryowire spec](https://cryowire.github.io/spec/) format:

```
output/
├── metadata.yaml
├── chip.yaml
├── control.yaml
├── readout_send.yaml
└── readout_return.yaml
```

## Interactive notebook

For a hands-on experience, try the [Playground](playground.md) or run the tutorial locally:

```bash
pip install cryowire jupyter
jupyter notebook examples/notebooks/tutorial.ipynb
```
