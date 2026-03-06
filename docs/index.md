# Cryo Wiring Core

Python library for dilution refrigerator wiring configuration — data models, validation, diagram generation, and programmatic building.

## Features

| Module     | Description                                               |
| ---------- | --------------------------------------------------------- |
| `models`   | Pydantic v2 models (Stage, Component types, WiringConfig) |
| `validate` | JSON Schema validation against cryo-wiring-spec           |
| `loader`   | YAML loading, module expansion, component catalog         |
| `builder`  | Programmatic cooldown generation from Python code         |
| `summary`  | Wiring summary tables (terminal, Markdown, HTML)          |
| `diagram`  | Publication-quality wiring diagrams (matplotlib)          |

## Installation

```bash
pip install cryo-wiring-core
```

## Try it online

The [Playground](../marimo/) lets you run the getting-started notebook directly in your browser — no installation required.

## Related Repositories

| Repository | Description |
| --- | --- |
| [cryo-wiring/spec](https://cryo-wiring.github.io/spec/) | YAML format specification & schemas |
| [cryo-wiring/cli](https://github.com/cryo-wiring/cli) | CLI tool |
| [cryo-wiring/app](https://github.com/cryo-wiring/app) | Web UI (FastAPI + Next.js) |
| [cryo-wiring/template](https://github.com/cryo-wiring/template) | Data repository template |
