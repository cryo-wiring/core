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

The [Playground](../marimo/) lets you run the getting-started notebook directly in your browser — no installation required.

## Related Repositories

| Repository | Description |
| --- | --- |
| [cryowire/spec](https://cryowire.github.io/spec/) | YAML format specification & schemas |
| [cryowire/cli](https://github.com/cryowire/cli) | CLI tool |
| [cryowire/app](https://github.com/cryowire/app) | Web UI (FastAPI + Next.js) |
| [cryowire/template](https://github.com/cryowire/template) | Data repository template |
