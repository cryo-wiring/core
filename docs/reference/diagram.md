# Diagram

::: cryowire.diagram

## generate_diagram()

```python
generate_diagram(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
    output: str | Path = "wiring.svg",
    filter_lines: list[str] | None = None,
    representative: bool = False,
    width: float = 3.375,
) -> Path
```

### Parameters

| Parameter | Description |
| --- | --- |
| `output` | Output file path. Format inferred from extension. |
| `filter_lines` | Draw only the specified line IDs. |
| `representative` | Draw one line per type (control, RS, RR). |
| `width` | Figure width in inches (default 3.375 = Nature single-column). |
