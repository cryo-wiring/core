# Models

::: cryo_wiring_core.models

## Stage

Temperature stages in a dilution refrigerator, ordered from top to bottom:

| Stage    | Value    | Temperature |
| -------- | -------- | ----------- |
| `RT`     | `"RT"`   | Room temp   |
| `K50`    | `"50K"`  | 50 K        |
| `K4`     | `"4K"`   | 4 K         |
| `STILL`  | `"Still"`| ~800 mK     |
| `CP`     | `"CP"`   | ~100 mK     |
| `MXC`    | `"MXC"`  | ~10 mK      |

## Component types

| Class             | Key fields                    | Diagram label   |
| ----------------- | ----------------------------- | --------------- |
| `Attenuator`      | `value_dB`                    | `10 dB`         |
| `Filter`          | `filter_type`                 | `Ecco.` / `FLT` |
| `Isolator`        | —                             | `ISO`           |
| `Amplifier`       | `amplifier_type`, `gain_dB`   | `+40 dB`        |
| `CustomComponent` | `custom_type`                 | user-defined    |

All components share `model` and `serial` fields, and expose `label`, `summary_label`, `attenuation`, `gain` properties.

## Line models

- `ControlLine` — `line_id` pattern `C\d+`, single `qubit`
- `ReadoutLine` — `line_id` pattern `(RS|RR)\d+`, list of `qubits`

## Configuration models

- `WiringConfig` — contains `lines: list[ControlLine | ReadoutLine]`
- `CooldownMetadata` — cooldown ID, date, fridge, operator, purpose
- `ChipConfig` — chip name and qubit count
