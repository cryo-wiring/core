# Diagram

Generate publication-quality wiring diagrams suitable for single-column academic papers (Nature / PRL).

## Usage

```python
cooldown = CooldownBuilder(num_qubits=8).control_module(...).build()

# Representative diagram (one line per type)
cooldown.diagram(output="wiring.svg", representative=True)

# All lines
cooldown.diagram(output="wiring.svg")

# Specific lines only
cooldown.diagram(output="wiring.svg", filter_lines=["C00", "RS00", "RR00"])

# Custom width (inches)
cooldown.diagram(output="wiring.pdf", width=6.5)
```

## Output formats

The output format is determined by the file extension:

| Extension | Format |
| --------- | ------ |
| `.svg`    | SVG    |
| `.pdf`    | PDF    |
| `.png`    | PNG    |

## Standalone function

```python
from cryo_wiring_core import generate_diagram

generate_diagram(control, readout_send, readout_return, output="wiring.svg")
```

## Layout

The diagram shows:

- **Stage bands** — horizontal bands for RT, 50K, 4K, Still, CP, MXC
- **Wiring lines** — vertical lines with components drawn as labeled boxes
- **Line styles** — solid (control), dashed (readout send), dash-dot (readout return)
- **Direction arrows** — indicating signal flow
- **DUT box** — at the bottom below MXC
