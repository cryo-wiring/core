"""CLI interface for cryowire configuration manager."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

import yaml

from cryowire.builder import build_cooldown
from cryowire.bundle import write_cooldown
from cryowire.config import resolve_template_path
from cryowire.diagram import generate_diagram
from cryowire.layout import CryoLayout
from cryowire.loader import (
    bundled_templates_dir,
    expand_modules,
    load_chip,
    load_components,
    load_cooldown,
    load_yaml,
)
from cryowire.models import ChipConfig
from cryowire.summary import generate_markdown_table, print_summary
from cryowire.validate import (
    validate_chip,
    validate_components,
    validate_metadata,
    validate_wiring,
)
from jsonschema import ValidationError

app = typer.Typer(help="Dilution refrigerator wiring configuration manager.")
console = Console()


_CRYOWIRE_YAML = """\
# cryowire project configuration
# See: https://github.com/cryowire/spec

# Path to template files (modules, metadata template, etc.)
# Relative paths are resolved from this file's directory.
template_path: ./templates
"""


def _find_components_path(cooldown_dir: Path) -> Path | None:
    """Locate components.yaml in the cooldown dir or its ancestors."""
    d = cooldown_dir.resolve()
    while True:
        p = d / "components.yaml"
        if p.exists():
            return p
        parent = d.parent
        if parent == d:
            break
        d = parent
    return None


@app.command()
def init(
    directory: Annotated[Path, typer.Argument(help="Directory to initialize (default: current)")] = Path("."),
) -> None:
    """Initialize a new cryowire data project.

    Generates .cryowire.yaml, components.yaml, and templates/ directory.
    """
    target = directory.resolve()
    target.mkdir(parents=True, exist_ok=True)

    # .cryowire.yaml
    config_path = target / ".cryowire.yaml"
    if config_path.exists():
        console.print(f"[bold red]Already initialized:[/] {config_path}")
        raise typer.Exit(1)
    config_path.write_text(_CRYOWIRE_YAML)
    console.print(f"  [green]{config_path.relative_to(target)}[/]")

    # components.yaml
    bundled = bundled_templates_dir()
    comp_src = bundled / "components.yaml"
    comp_dst = target / "components.yaml"
    shutil.copy2(comp_src, comp_dst)
    console.print(f"  [green]{comp_dst.relative_to(target)}[/]")

    # templates/
    templates_dst = target / "templates"
    templates_dst.mkdir(exist_ok=True)
    for src_file in sorted(bundled.iterdir()):
        if src_file.name == "components.yaml":
            continue
        if src_file.is_file() and src_file.suffix == ".yaml":
            shutil.copy2(src_file, templates_dst / src_file.name)
            console.print(f"  [green]{(templates_dst / src_file.name).relative_to(target)}[/]")

    console.print("[bold green]Initialized.[/]")


@app.command()
def validate(cooldown_dir: Annotated[Path, typer.Argument(help="Cooldown directory path")]) -> None:
    """Validate wiring YAML files with JSON Schema and pydantic."""
    errors: list[str] = []

    wiring_files = ["control.yaml", "readout_send.yaml", "readout_return.yaml"]
    # Backward compat: if readout_send.yaml missing, check old readout_return.yaml only
    if not (cooldown_dir / "readout_send.yaml").exists():
        wiring_files = ["control.yaml", "readout_return.yaml"]

    for name in wiring_files:
        yaml_path = cooldown_dir / name
        if not yaml_path.exists():
            errors.append(f"{name}: file not found")
            continue
        data = load_yaml(yaml_path)
        try:
            validate_wiring(data)
        except ValidationError as e:
            errors.append(f"{name} (schema): {e.message}")

    # Validate metadata
    meta_path = cooldown_dir / "metadata.yaml"
    if meta_path.exists():
        try:
            validate_metadata(load_yaml(meta_path))
        except ValidationError as e:
            errors.append(f"metadata.yaml (schema): {e.message}")

    # Validate components
    comp_path = _find_components_path(cooldown_dir)
    if comp_path is not None:
        try:
            validate_components(load_yaml(comp_path))
        except ValidationError as e:
            errors.append(f"components.yaml (schema): {e.message}")

    # Validate chip
    for chip_candidate in (cooldown_dir / "chip.yaml", cooldown_dir.parent / "chip.yaml"):
        if chip_candidate.exists():
            try:
                validate_chip(load_yaml(chip_candidate))
            except ValidationError as e:
                errors.append(f"chip.yaml (schema): {e.message}")
            break

    # Pydantic validation
    try:
        load_cooldown(cooldown_dir, components_path=comp_path)
    except Exception as e:
        errors.append(f"pydantic: {e}")

    if errors:
        console.print("[bold red]Validation failed:[/]")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(1)

    console.print("[bold green]Validation passed.[/]")


@app.command()
def new(
    cryo: Annotated[str, typer.Argument(help="Cryostat name (e.g. your-cryo)")],
    qubits: Annotated[Optional[int], typer.Option("--qubits", help="Number of qubits")] = None,
    chip_name: Annotated[Optional[str], typer.Option("--chip-name", help="Chip name")] = None,
    chip: Annotated[Optional[Path], typer.Option("--chip", help="Path to chip.yaml")] = None,
    cooldown_date: Annotated[Optional[str], typer.Option("--date", help="Date (YYYY-MM-DD)")] = None,
    template_path: Annotated[Optional[Path], typer.Option("--template-path", help="Custom templates directory")] = None,
    data_dir: Annotated[Path, typer.Option("--data-dir", help="Data root directory")] = Path("."),
) -> None:
    """Create a new cooldown for a cryostat.

    Generates <cryo>/<YYYY>/cdNNN/ with template wiring files.
    Specify chip inline (--qubits/--chip-name) or via file (--chip).
    """
    if chip is not None and qubits is not None:
        console.print("[bold red]Cannot use both --chip and --qubits.[/]")
        raise typer.Exit(1)

    if chip is not None:
        chip_cfg = load_chip(chip)
    elif qubits is not None:
        chip_cfg = ChipConfig(name=chip_name or f"chip-{qubits}q", num_qubits=qubits)
    else:
        console.print("[bold red]Specify --qubits or --chip.[/]")
        raise typer.Exit(1)

    layout = CryoLayout(data_dir)

    year = (cooldown_date or str(date.today())).split("-")[0]
    cooldown_id = layout.next_cooldown_id(cryo, year)
    target = layout.cooldown_path(cryo, year, cooldown_id)

    if target.exists():
        console.print(f"[bold red]Directory already exists: {target}[/]")
        raise typer.Exit(1)

    # Resolve template path: explicit > .cryowire.yaml > bundled
    tpath = resolve_template_path(explicit=template_path, search_from=data_dir)

    comp_path = data_dir / "components.yaml"

    build_cooldown(
        output_dir=target,
        cryo=cryo,
        chip_name=chip_cfg.name,
        num_qubits=chip_cfg.num_qubits,
        cooldown_id=cooldown_id,
        cooldown_date=cooldown_date,
        template_path=tpath,
        components_path=comp_path if comp_path.exists() else None,
    )

    # Copy or generate chip.yaml into cooldown directory
    if chip is not None:
        shutil.copy2(chip, target / "chip.yaml")

    # Generate cooldown.yaml bundle
    write_cooldown(target, components_path=comp_path if comp_path.exists() else None)

    console.print(f"[bold green]Created:[/] {target.relative_to(data_dir.resolve())} ({chip_cfg.num_qubits} qubits)")


@app.command()
def diagram(
    cooldown_dir: Annotated[Path, typer.Argument(help="Cooldown directory path")],
    output: Annotated[str, typer.Option("-o", "--output", help="Output file (SVG/PNG)")] = "wiring.svg",
    line: Annotated[Optional[list[str]], typer.Option("-l", "--line", help="Filter by line ID")] = None,
    width: Annotated[float, typer.Option("--width", help="Figure width in inches")] = 3.375,
) -> None:
    """Generate a wiring diagram."""
    comp_path = _find_components_path(cooldown_dir)
    metadata, control, readout_send, readout_return = load_cooldown(cooldown_dir, components_path=comp_path)
    out = generate_diagram(
        control, readout_send, readout_return,
        output=output, filter_lines=line, width=width, metadata=metadata,
    )
    console.print(f"[bold green]Diagram saved:[/] {out}")


@app.command()
def build(
    cooldown_dir: Annotated[Path, typer.Argument(help="Cooldown directory path")],
    width: Annotated[float, typer.Option("--width", help="Figure width in inches")] = 3.375,
) -> None:
    """Expand module YAML, generate cooldown.yaml, wiring diagram and README."""
    build_dir = cooldown_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Load component catalog for module expansion
    comp_path = _find_components_path(cooldown_dir)
    catalog = load_components(comp_path) if comp_path else {}

    # 1. Expand module YAML into flat format
    wiring_files = ["control.yaml", "readout_send.yaml", "readout_return.yaml"]
    if not (cooldown_dir / "readout_send.yaml").exists():
        wiring_files = ["control.yaml", "readout_return.yaml"]

    for name in wiring_files:
        src = cooldown_dir / name
        if not src.exists():
            continue
        data = load_yaml(src)
        expanded = expand_modules(data, catalog)
        dest = build_dir / name
        dest.write_text(yaml.dump(expanded, default_flow_style=False, allow_unicode=True, sort_keys=False))
        console.print(f"  [green]{dest}[/]")

    # 2. Generate cooldown.yaml bundle
    out_yaml = write_cooldown(cooldown_dir, components_path=comp_path)
    console.print(f"  [green]{out_yaml}[/]")

    # 3. Load cooldown and generate diagram + README
    metadata, control, readout_send, readout_return = load_cooldown(cooldown_dir, components_path=comp_path)

    svg_path = cooldown_dir / "wiring.svg"
    generate_diagram(
        control, readout_send, readout_return,
        output=svg_path, representative=True, width=width, metadata=metadata,
    )
    console.print(f"  [green]{svg_path}[/]")

    # 4. Generate README.md
    table_md = generate_markdown_table(
        control, readout_send, readout_return, metadata=metadata, diagram="wiring.svg",
    )
    readme_lines = [
        f"# {metadata.cooldown_id} — {metadata.date}",
        "",
        f"- **Cryo**: {metadata.cryo}",
    ]
    chip_path = cooldown_dir / "chip.yaml"
    if not chip_path.exists():
        chip_path = cooldown_dir.parent / "chip.yaml"
    if chip_path.exists():
        chip_cfg = load_chip(chip_path)
        readme_lines.append(f"- **Chip**: {chip_cfg.name} ({chip_cfg.num_qubits}Q)")
    if metadata.operator:
        readme_lines.append(f"- **Operator**: {metadata.operator}")
    if metadata.purpose:
        readme_lines.append(f"- **Purpose**: {metadata.purpose}")
    if metadata.notes:
        readme_lines += ["", "## Notes", "", metadata.notes.strip()]
    readme_lines += [
        "",
        table_md,
        "",
    ]

    readme_path = cooldown_dir / "README.md"
    readme_path.write_text("\n".join(readme_lines) + "\n")
    console.print(f"  [green]{readme_path}[/]")

    console.print("[bold green]Build complete.[/]")


@app.command()
def summary(
    cooldown_dir: Annotated[Path, typer.Argument(help="Cooldown directory path")],
    fmt: Annotated[str, typer.Option("--format", help="Output format: terminal, html, or markdown")] = "terminal",
    line_type: Annotated[str, typer.Option("--type", help="Line type: control, readout_send, readout_return, or all")] = "all",
    output: Annotated[Optional[str], typer.Option("-o", "--output", help="Output file")] = None,
) -> None:
    """Print wiring summary table."""
    comp_path = _find_components_path(cooldown_dir)
    metadata, control, readout_send, readout_return = load_cooldown(cooldown_dir, components_path=comp_path)
    print_summary(
        control, readout_send, readout_return,
        line_type=line_type, fmt=fmt, output=output, metadata=metadata,
    )


if __name__ == "__main__":
    app()
