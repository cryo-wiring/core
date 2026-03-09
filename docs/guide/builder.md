# Builder

The `CooldownBuilder` provides a fluent API for constructing wiring configurations from Python component objects.

## Basic usage

```python
from cryo_wiring_core import CooldownBuilder, Attenuator, Filter, Stage

cooldown = (
    CooldownBuilder(num_qubits=8)
    .control_module("ctrl", {
        Stage.K50: [Attenuator(model="XMA-10dB", value_dB=10)],
        Stage.MXC: [Attenuator(model="XMA-20dB", value_dB=20)],
    })
    .build()
)
```

## Modules

Three module types are supported:

| Method                   | Line prefix | Direction |
| ------------------------ | ----------- | --------- |
| `control_module()`       | `C`         | down      |
| `readout_send_module()`  | `RS`        | down      |
| `readout_return_module()` | `RR`       | up        |

Each takes a module name and a `dict[Stage, list[Component]]` defining the default components per stage.

## Per-line overrides

### Single line

```python
builder.add("C00", Stage.STILL, Filter(model="K&L", filter_type="Lowpass"))
builder.remove("C00", Stage.MXC, component_type="filter")
builder.replace("C00", Stage.K4, 0, Attenuator(model="XMA-10dB", value_dB=10))
```

### Bulk overrides

```python
builder.for_lines("C03", "C05")
    .remove(Stage.MXC, component_type="filter")
    .replace(Stage.K4, 0, Attenuator(model="XMA-10dB", value_dB=10))
.end()
```

## Result object

`build()` returns a `Cooldown` object with:

- `cooldown.control` / `cooldown.readout_send` / `cooldown.readout_return` — `WiringConfig` objects
- `cooldown.summary(fmt=...)` — generate summary tables
- `cooldown.diagram(output=...)` — generate wiring diagrams
- `cooldown.write(output_dir, cryo=...)` — export YAML files
- Supports unpacking: `control, rs, rr = cooldown`

## Template-based generation

For generating from bundled templates instead of component objects:

```python
from cryo_wiring_core import build_cooldown

build_cooldown(
    output_dir="anemone/current",
    cryo="your-cryo",
    chip_name="sample-chip",
    num_qubits=16,
)
```
