# Summary

The summary module generates wiring summary tables in multiple formats.

## Formats

| Format     | Method                          | Output          |
| ---------- | ------------------------------- | --------------- |
| Terminal   | `cooldown.summary()`            | Rich table      |
| Markdown   | `cooldown.summary(fmt="markdown")` | `str`       |
| HTML       | `cooldown.summary(fmt="html")`  | `str`           |

## Usage

```python
cooldown = CooldownBuilder(num_qubits=8).control_module(...).build()

# Print to terminal (requires `rich`)
cooldown.summary()

# Get Markdown string
md = cooldown.summary(fmt="markdown")

# Get HTML string
html = cooldown.summary(fmt="html")
```

## Filtering by line type

```python
cooldown.summary(line_type="control")
cooldown.summary(line_type="readout_send")
cooldown.summary(line_type="readout_return")
```

## Standalone functions

For use with `WiringConfig` objects directly:

```python
from cryowire import print_summary, generate_markdown_table, generate_html_table

print_summary(control, readout_send, readout_return)
md = generate_markdown_table(control, readout_send, readout_return)
html = generate_html_table(control, readout_send, readout_return)
```
