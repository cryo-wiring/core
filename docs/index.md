# Cryo Wiring Core

Python library for dilution refrigerator wiring configuration — data models, validation, diagram generation, and programmatic building.

## Features

| Module     | Description                                               |
| ---------- | --------------------------------------------------------- |
| `models`   | Pydantic v2 models (Stage, Component types, WiringConfig) |
| `validate` | JSON Schema validation against cryowire-spec           |
| `loader`   | YAML loading, module expansion, component catalog         |
| `builder`  | Programmatic cooldown generation from Python code         |
| `summary`  | Wiring summary tables (terminal, Markdown, HTML)          |
| `diagram`  | Publication-quality wiring diagrams (matplotlib)          |

## Installation

```bash
pip install cryowire
```

## Try it online

The [Playground](playground.md) lets you run the getting-started notebook directly in your browser — no installation required.

See **[cryowire.github.io](https://cryowire.github.io/)** for the full project overview.
