# Summary

::: cryowire.summary

## Functions

| Function | Description |
| --- | --- |
| `print_summary(control, rs, rr, fmt=, output=)` | Print or export summary |
| `generate_markdown_table(control, rs, rr)` | Generate Markdown summary |
| `generate_html_table(control, rs, rr)` | Generate HTML summary |
| `grouped_summaries(control, rs, rr)` | Return structured summary data |
| `line_summary(line)` | Compute summary for a single line |

## Formats

- `"terminal"` — Rich table printed to stdout
- `"markdown"` — Markdown string with tables per section
- `"html"` — HTML string with tables per section
