import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Cryo Wiring Core - Getting Started

    This notebook demonstrates the main features of `cryo-wiring-core`:

    1. **Builder** - Programmatically define wiring configurations
    2. **Per-line overrides** - Add / remove / replace components on individual lines
    3. **Summary** - View wiring summaries as tables
    4. **Diagram** - Generate publication-quality wiring diagrams
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


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
        CooldownBuilder,
        Filter,
        Isolator,
        Stage,
    )

    cooldown = (
        CooldownBuilder(num_qubits=8)
        .control_module(
            "ctrl",
            {
                Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
                Stage.K4: [Attenuator(model="XMA-2082-6431-20", value_dB=20)],
                Stage.MXC: [
                    Attenuator(model="XMA-2082-6431-20", value_dB=20),
                    Filter(model="XMA-EF-03", filter_type="Eccosorb"),
                ],
            },
        )
        .readout_send_module(
            "rs",
            {
                Stage.K50: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
                Stage.K4: [Attenuator(model="XMA-2082-6431-10", value_dB=10)],
            },
        )
        .readout_return_module(
            "rr",
            {
                Stage.RT: [Amplifier(model="MITEQ-AFS3", amplifier_type="RT", gain_dB=20)],
                Stage.K50: [Amplifier(model="LNF-LNC03_14A", amplifier_type="HEMT", gain_dB=40)],
                Stage.CP: [Isolator(model="LNF-ISC4_12A"), Isolator(model="LNF-ISC4_12A")],
            },
        )
        # -- Per-line overrides --
        # Add a filter at Still on C00
        .add("C00", Stage.STILL, Filter(model="K&L-5VLF", filter_type="Lowpass"))
        # Bulk override: drop MXC filter and swap 4K attenuator on C03 and C05
        .for_lines("C03", "C05")
            .remove(Stage.MXC, component_type="filter")
            .replace(Stage.K4, 0, Attenuator(model="XMA-2082-6431-10", value_dB=10))
        .end()
        # Remove second isolator at CP on RR00
        .remove("RR00", Stage.CP, index=1)
        .build()
    )
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
    import tempfile
    from pathlib import Path as _Path

    _tmpfile = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
    cooldown.diagram(output=_tmpfile.name, representative=True)
    _svg_content = _Path(_tmpfile.name).read_text()
    mo.Html(_svg_content)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Write YAML files

    `cooldown.write()` exports the configuration as a set of YAML files
    that follow the [cryo-wiring spec](https://github.com/cryo-wiring/spec).
    """)
    return


@app.cell
def _(cooldown, mo):
    from pathlib import Path as _Path

    _output_dir = _Path(__file__).parent / "output"
    _result = cooldown.write(_output_dir, fridge="anemone", chip_name="sample-8q")
    _files = sorted(f.name for f in _result.iterdir() if f.suffix == ".yaml")
    mo.md(f"Wrote to `{_result}`:\n\n" + "\n".join(f"- `{f}`" for f in _files))
    return


if __name__ == "__main__":
    app.run()
