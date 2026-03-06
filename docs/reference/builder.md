# Builder

::: cryo_wiring_core.builder

## CooldownBuilder

Fluent builder for constructing wiring configurations from component models.

### Methods

| Method | Description |
| --- | --- |
| `control_module(name, stages)` | Define control module |
| `readout_send_module(name, stages)` | Define readout-send module |
| `readout_return_module(name, stages)` | Define readout-return module |
| `add(line_ids, stage, component)` | Add component to line(s) |
| `remove(line_ids, stage, ...)` | Remove component(s) from line(s) |
| `replace(line_ids, stage, index, component)` | Replace component on line(s) |
| `for_lines(*line_ids)` | Start scoped bulk override |
| `build()` | Build `Cooldown` result |
| `write(output_dir, fridge=, ...)` | Export as YAML directory |

## Cooldown

Result object returned by `CooldownBuilder.build()`.

### Attributes

- `control` — `WiringConfig`
- `readout_send` — `WiringConfig`
- `readout_return` — `WiringConfig`

### Methods

- `summary(fmt="terminal")` — print or return summary
- `diagram(output="wiring.svg", ...)` — generate diagram
- `write(output_dir, fridge=, ...)` — export YAML files

## build_cooldown()

Template-based generation from bundled YAML templates.

```python
build_cooldown(output_dir, fridge, chip_name, num_qubits, ...)
```
