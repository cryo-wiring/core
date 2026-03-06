# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "pydantic>=2.0",
#     "pyyaml>=6.0",
#     "jsonschema>=4.23",
#     "matplotlib>=3.7",
#     "rich>=13.0",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
async def _():
    import marimo as mo
    import sys as _sys

    # Install cryo-wiring-core in Pyodide (WASM) environment
    if "pyodide" in _sys.modules:
        import micropip as _micropip

        await _micropip.install(
            ["jsonschema", "matplotlib", "pydantic", "pyyaml", "rich"]
        )
        _WHEEL = "cryo_wiring_core-0.1.0-py3-none-any.whl"
        try:
            await _micropip.install(f"./files/{_WHEEL}", deps=False)
        except Exception:
            await _micropip.install(
                f"https://cryo-wiring.github.io/core/marimo/files/{_WHEEL}",
                deps=False,
            )
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Cryo Wiring Core - Getting Started

    This notebook demonstrates the main features of `cryo-wiring-core`:

    1. **Builder** - Programmatically define wiring configurations
    2. **Per-line overrides** - Add / remove / replace components on individual lines
    3. **Summary** - View wiring summaries as tables
    4. **Diagram** - Generate publication-quality wiring diagrams
    5. **Export** - Save summary (Markdown) and diagram (SVG) to files
    6. **Bundle** - Export a single-file YAML bundle for viewers and sharing
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Build a cooldown configuration

    `CooldownBuilder` supports full method chaining.
    Define modules, apply per-line overrides, and call `.build()` in a single expression.
    """)
    return


@app.cell
def _():
    from cryo_wiring_core import (
        Amplifier,
        Attenuator,
        ChipConfig,
        CooldownBuilder,
        CooldownMetadata,
        Filter,
        Isolator,
        Stage,
    )

    # Component catalog
    catalog = {
        "XMA-10dB": Attenuator(manufacturer="XMA", model="2082-6431-10", value_dB=10),
        "XMA-20dB": Attenuator(manufacturer="XMA", model="2082-6431-20", value_dB=20),
        "Eccosorb": Filter(manufacturer="XMA", model="EF-03", filter_type="Eccosorb"),
        "K&L-LPF": Filter(manufacturer="K&L", model="5VLF", filter_type="Lowpass"),
        "RT-AMP": Amplifier(manufacturer="MITEQ", model="AFS3", amplifier_type="RT", gain_dB=20),
        "LNF-HEMT": Amplifier(manufacturer="LNF", model="LNC03_14A", amplifier_type="HEMT", gain_dB=40),
        "LNF-ISO": Isolator(manufacturer="LNF", model="ISC4_12A"),
    }

    # Build cooldown
    cooldown = (
        CooldownBuilder(
            chip=ChipConfig(name="sample-8q", num_qubits=8, qubits_per_readout_line=4),
            metadata=CooldownMetadata(fridge="your-cryo", cooldown_id="cd001", date="2026-03-06"),
            catalog=catalog,
            control={
                Stage.K50: ["XMA-10dB"],
                Stage.K4: ["XMA-20dB"],
                Stage.MXC: ["XMA-20dB", "Eccosorb"],
            },
            readout_send={Stage.K50: ["XMA-10dB"], Stage.K4: ["XMA-10dB"]},
            readout_return={
                Stage.RT: ["RT-AMP"],
                Stage.K50: ["LNF-HEMT"],
                Stage.CP: ["LNF-ISO", "LNF-ISO"],
            },
        )
        .add("C00", Stage.STILL, "K&L-LPF")
        .remove("RR00", Stage.CP, index=1)
        .build()
    )

    # Per-line overrides
    with cooldown.for_lines("C03", "C05") as lines:
        lines.remove(Stage.MXC, component_type=Filter)
        lines.replace(Stage.K4, 0, "XMA-10dB")

    return (cooldown,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Wiring summary

    Call `cooldown.summary()` directly — no need to import separate functions.
    """)
    return


@app.cell
def _(cooldown, mo):
    _html = cooldown.summary(fmt="html")
    mo.Html(_html)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Wiring diagram
    """)
    return


@app.cell
def _(cooldown, mo):
    import tempfile as _tempfile
    from pathlib import Path as _Path

    _tmpfile = _tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
    cooldown.diagram(output=_tmpfile.name, representative=True)
    _svg_content = _Path(_tmpfile.name).read_text()
    mo.Html(_svg_content)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Export summary and diagram

    Save the wiring summary as Markdown and the diagram as SVG to the output directory.
    """)
    return


@app.cell
def _(cooldown, mo):
    import tempfile as _tempfile
    from pathlib import Path as _Path

    _output_dir = _Path(_tempfile.mkdtemp()) / "export"
    _output_dir.mkdir(parents=True, exist_ok=True)

    # SVG diagram
    cooldown.diagram(output=_output_dir / "wiring.svg", representative=True)

    # Markdown summary with diagram embedded
    _md_content = cooldown.summary(fmt="markdown", diagram="wiring.svg")
    (_output_dir / "README.md").write_text(_md_content)

    mo.md(
        f"Exported to `{_output_dir}`:\n\n"
        f"- `summary.md`\n"
        f"- `wiring.svg`"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Write YAML files

    `cooldown.write()` exports the configuration as a set of YAML files
    that follow the [cryo-wiring spec](https://github.com/cryo-wiring/spec).
    """)
    return


@app.cell
def _(cooldown, mo):
    import tempfile as _tempfile
    from pathlib import Path as _Path

    _output_dir = _Path(_tempfile.mkdtemp()) / "output"
    _result = cooldown.write(_output_dir)
    _files = sorted(f.name for f in _result.iterdir() if f.suffix == ".yaml")
    mo.md(f"Wrote to `{_result}`:\n\n" + "\n".join(f"- `{f}`" for f in _files))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Export as a single-file bundle

    `write_cooldown()` generates a fully-resolved YAML file containing metadata,
    chip info, all wiring lines (expanded), and pre-computed summaries.
    Viewers only need to read this one file — no module expansion or component
    resolution required.
    """)
    return


@app.cell
def _(cooldown, mo):
    import tempfile as _tempfile
    from pathlib import Path as _Path

    from cryo_wiring_core.bundle import write_cooldown

    _output_dir = _Path(_tempfile.mkdtemp()) / "output"
    _result = cooldown.write(_output_dir)
    _cooldown_path = write_cooldown(
        _output_dir,
        components_path=_output_dir / "components.yaml",
    )
    _size = _cooldown_path.stat().st_size
    mo.md(
        f"Wrote `{_cooldown_path.name}` ({_size:,} bytes) — a single file containing "
        f"the entire resolved cooldown.\n\n"
        f"```yaml\n{_cooldown_path.read_text()[:500]}...\n```"
    )
    return


if __name__ == "__main__":
    app.run()
