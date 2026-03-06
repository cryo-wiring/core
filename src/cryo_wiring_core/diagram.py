"""Publication-quality wiring diagram for dilution refrigerator.

Generates a block-diagram style figure suitable for single-column
academic papers (Nature / PRL).  Default width is 86 mm (3.375 in).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from cryo_wiring_core.models import (
    Amplifier,
    Attenuator,
    ControlLine,
    Filter,
    Isolator,
    ReadoutLine,
    Stage,
    STAGE_ORDER,
    WiringConfig,
)

# -- Publication rcParams --
_RC = {
    "font.family": "serif",
    "mathtext.fontset": "cm",
    "axes.linewidth": 0.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}

# Font sizes (pt)
_FS_STAGE = 7
_FS_COMP = 5.5
_FS_LINE_ID = 5.5

# -- Grayscale-friendly palette --
_BAND_FILLS = ("#F5F5F5", "#EBEBEB")
_BAND_EDGE = "#BBBBBB"
_LINE_COLOR = "black"

# -- Layout constants (data-coordinate space) --
_COMP_W = 0.20          # component box half-width
_COMP_H = 0.065         # component box half-height
_COMP_PITCH = 0.16      # vertical pitch between stacked components
_LINE_SPACING = 0.50    # horizontal pitch between wiring lines
_LABEL_MARGIN = 0.55    # space for stage labels (left of bands)
_BAND_PAD_H = 0.12      # horizontal padding inside band beyond outermost component
_HEADER_HEIGHT = 0.40   # space above top band for line ID labels
_MIN_BAND_HEIGHT = 0.25 # minimum band height (for stages with no components)
_BAND_PAD_V = 0.10      # vertical padding above/below components inside a band
_DOT_SIZE = 1.5
_DUT_HEIGHT = 0.20      # DUT box height
_DUT_GAP = 0.08         # gap between MXC band bottom and DUT box
_ARROW_SIZE = 0.06      # arrow head size for direction indicators


def _comp_label(comp) -> str:
    """Short label for a component."""
    if isinstance(comp, Attenuator):
        return f"{comp.value_dB:.0f} dB"
    if isinstance(comp, Filter):
        if comp.filter_type:
            name = comp.filter_type
            return "Ecco." if name.lower().startswith("ecco") else name[:5]
        return "FLT"
    if isinstance(comp, Isolator):
        return "ISO"
    if isinstance(comp, Amplifier):
        return f"+{comp.gain_dB:.0f} dB"
    return "?"


def _max_components_per_stage(
    lines: list[ControlLine | ReadoutLine],
) -> dict[Stage, int]:
    """For each stage, find the max number of components any line has there."""
    counts: dict[Stage, int] = {s: 0 for s in STAGE_ORDER}
    for line in lines:
        for stage in STAGE_ORDER:
            n = len(line.stages.get(stage, []))
            if n > counts[stage]:
                counts[stage] = n
    return counts


def _compute_band_layout(
    lines: list[ControlLine | ReadoutLine],
) -> tuple[dict[Stage, float], dict[Stage, float]]:
    """Compute contiguous band positions.

    Returns (stage_y_centre, stage_band_height) dicts.
    Bands are stacked top-to-bottom with no gaps.
    """
    max_comp = _max_components_per_stage(lines)
    heights: dict[Stage, float] = {}
    for stage in STAGE_ORDER:
        n = max_comp[stage]
        if n == 0:
            heights[stage] = _MIN_BAND_HEIGHT
        else:
            heights[stage] = max(
                _MIN_BAND_HEIGHT,
                n * _COMP_PITCH + 2 * _BAND_PAD_V,
            )

    # Stack from y=0 downward
    y_centres: dict[Stage, float] = {}
    y_cursor = 0.0
    for stage in STAGE_ORDER:
        h = heights[stage]
        y_centres[stage] = y_cursor - h / 2
        y_cursor -= h

    return y_centres, heights


# -- Drawing helpers --

def _draw_stages(
    ax: plt.Axes,
    x_left: float,
    x_right: float,
    stage_y: dict[Stage, float],
    stage_h: dict[Stage, float],
) -> None:
    """Draw contiguous horizontal stage bands with labels."""
    for i, stage in enumerate(STAGE_ORDER):
        yc = stage_y[stage]
        h = stage_h[stage]
        fill = _BAND_FILLS[i % 2]
        rect = mpatches.Rectangle(
            (x_left, yc - h / 2),
            x_right - x_left,
            h,
            facecolor=fill,
            edgecolor=_BAND_EDGE,
            linewidth=0.4,
            zorder=0,
        )
        ax.add_patch(rect)
        ax.text(
            x_left - 0.04, yc, stage.value,
            ha="right", va="center",
            fontsize=_FS_STAGE, color="#333333",
        )


def _draw_component(ax: plt.Axes, x: float, y: float, comp) -> None:
    """Draw a clean rectangle with label."""
    rect = mpatches.Rectangle(
        (x - _COMP_W, y - _COMP_H),
        _COMP_W * 2, _COMP_H * 2,
        facecolor="white",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )
    ax.add_patch(rect)
    ax.text(
        x, y, _comp_label(comp),
        ha="center", va="center",
        fontsize=_FS_COMP, color="black", zorder=4,
    )


def _draw_line(
    ax: plt.Axes,
    line: ControlLine | ReadoutLine,
    x: float,
    stage_y: dict[Stage, float],
    linestyle: str = "-",
    direction: str = "down",
) -> None:
    """Draw one wiring line at horizontal position *x*."""
    is_control = isinstance(line, ControlLine)

    # Header label
    label = line.line_id
    if is_control:
        assert isinstance(line, ControlLine)
        label += f"\n({line.qubit})"
    else:
        assert isinstance(line, ReadoutLine)
        if direction == "up":
            label += f" out\n({line.qubits[0]}..{line.qubits[-1]})"
        else:
            label += f" in\n({line.qubits[0]}..{line.qubits[-1]})"

    top_y = stage_y[Stage.RT]
    ax.text(
        x, top_y + _HEADER_HEIGHT * 0.45, label,
        ha="center", va="bottom",
        fontsize=_FS_LINE_ID, color="black", linespacing=1.15,
    )

    # Draw continuous vertical line through all stages
    y_top = stage_y[STAGE_ORDER[0]]
    y_bottom = stage_y[STAGE_ORDER[-1]]

    # Extend line to cover components at bottom stage
    bottom_comps = line.stages.get(STAGE_ORDER[-1], [])
    if bottom_comps:
        n = len(bottom_comps)
        lowest_comp_y = stage_y[STAGE_ORDER[-1]]
        if n > 1:
            lowest_comp_y -= (n - 1) / 2 * _COMP_PITCH
        y_bottom = min(y_bottom, lowest_comp_y - _COMP_H)

    ax.plot(
        [x, x], [y_top, y_bottom],
        color=_LINE_COLOR, linewidth=0.6,
        linestyle=linestyle, zorder=1,
        solid_capstyle="round", dash_capstyle="round",
    )

    # Dots at each stage crossing
    for stage in STAGE_ORDER:
        ax.plot(x, stage_y[stage], "o", color=_LINE_COLOR, markersize=_DOT_SIZE, zorder=2)

    # Draw components at each stage
    for stage in STAGE_ORDER:
        components = line.stages.get(stage, [])
        n_comp = len(components)
        for j, comp in enumerate(components):
            cy = stage_y[stage]
            if n_comp > 1:
                cy += (j - (n_comp - 1) / 2) * _COMP_PITCH
            _draw_component(ax, x, cy, comp)

    # Direction arrow between first two stages
    first_stage = STAGE_ORDER[0] if direction == "down" else STAGE_ORDER[-1]
    second_stage = STAGE_ORDER[1] if direction == "down" else STAGE_ORDER[-2]
    arrow_y_mid = (stage_y[first_stage] + stage_y[second_stage]) / 2
    dy = -_ARROW_SIZE if direction == "down" else _ARROW_SIZE
    ax.annotate(
        "", xy=(x, arrow_y_mid + dy), xytext=(x, arrow_y_mid - dy),
        arrowprops=dict(
            arrowstyle="->", color=_LINE_COLOR,
            lw=0.8, shrinkA=0, shrinkB=0,
        ),
        zorder=5,
    )


def _draw_dut(
    ax: plt.Axes,
    x_left: float,
    x_right: float,
    y_top_edge: float,
    line_xs: list[float],
    stage_y_mxc: float,
) -> float:
    """Draw a DUT box below MXC and extend lines into it. Returns DUT bottom y."""
    dut_top = y_top_edge - _DUT_GAP
    dut_bottom = dut_top - _DUT_HEIGHT
    dut_cy = (dut_top + dut_bottom) / 2

    rect = mpatches.Rectangle(
        (x_left, dut_bottom),
        x_right - x_left,
        _DUT_HEIGHT,
        facecolor="white",
        edgecolor="black",
        linewidth=0.5,
        zorder=3,
    )
    ax.add_patch(rect)
    ax.text(
        (x_left + x_right) / 2, dut_cy, "DUT",
        ha="center", va="center",
        fontsize=_FS_STAGE, fontweight="bold", color="black", zorder=4,
    )

    # Short connector lines from MXC line endpoints into DUT box top
    for lx in line_xs:
        ax.plot(
            [lx, lx], [stage_y_mxc, dut_top],
            color=_LINE_COLOR, linewidth=0.6, zorder=1,
            solid_capstyle="round",
        )

    return dut_bottom


def _pick_representative(config: WiringConfig) -> list[ControlLine | ReadoutLine]:
    return [config.lines[0]] if config.lines else []


# -- Public API --

def generate_diagram(
    control: WiringConfig,
    readout_send: WiringConfig,
    readout_return: WiringConfig,
    output: str | Path = "wiring.svg",
    filter_lines: list[str] | None = None,
    representative: bool = False,
    width: float = 3.375,
) -> Path:
    """Generate a publication-quality wiring diagram.

    Parameters
    ----------
    width : float
        Figure width in inches (default 3.375 = Nature single-column).
    """
    # Build (line, linestyle, direction) triples for 3 line types:
    #   Control = solid/down, Readout Send = dashed/down, Readout Return = dash-dot/up
    line_info: list[tuple[ControlLine | ReadoutLine, str, str]] = []

    if representative:
        for l in _pick_representative(control):
            line_info.append((l, "-", "down"))
        for l in _pick_representative(readout_send):
            line_info.append((l, "--", "down"))
        for l in _pick_representative(readout_return):
            line_info.append((l, "-.", "up"))
    else:
        for l in control.lines:
            if filter_lines is None or l.line_id in filter_lines:
                line_info.append((l, "-", "down"))
        for l in readout_send.lines:
            if filter_lines is None or l.line_id in filter_lines:
                line_info.append((l, "--", "down"))
        for l in readout_return.lines:
            if filter_lines is None or l.line_id in filter_lines:
                line_info.append((l, "-.", "up"))

    if not line_info:
        raise ValueError("No lines to draw. Check --line filter.")

    all_lines: list[ControlLine | ReadoutLine] = [p[0] for p in line_info]
    n = len(all_lines)
    stage_y, stage_h = _compute_band_layout(all_lines)

    # X coordinates: lines centred, bands extend to cover component boxes
    x_first = _LABEL_MARGIN + _COMP_W + _BAND_PAD_H  # first line x
    x_last = x_first + (n - 1) * _LINE_SPACING
    band_left = x_first - _COMP_W - _BAND_PAD_H
    band_right = x_last + _COMP_W + _BAND_PAD_H
    x_max = band_right + 0.05

    # Y bounds (reserve space for DUT box below MXC)
    last_stage = STAGE_ORDER[-1]
    mxc_band_bottom = stage_y[last_stage] - stage_h[last_stage] / 2
    y_bottom = mxc_band_bottom - _DUT_GAP - _DUT_HEIGHT - 0.08
    y_top = _HEADER_HEIGHT + 0.15

    data_w = x_max
    data_h = y_top - y_bottom
    fig_height = width * (data_h / data_w)

    with mpl.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(width, fig_height))

        _draw_stages(ax, band_left, band_right, stage_y, stage_h)

        line_xs = []
        for i, (line, ls, direction) in enumerate(line_info):
            x = x_first + i * _LINE_SPACING
            line_xs.append(x)
            _draw_line(ax, line, x, stage_y, linestyle=ls, direction=direction)

        _draw_dut(ax, band_left, band_right, mxc_band_bottom, line_xs, stage_y[last_stage])

        # Legend (only when multiple line styles are present)
        has_styles = {ls for _, ls, _ in line_info}
        if len(has_styles) > 1:
            from matplotlib.lines import Line2D
            legend_items = []
            if "-" in has_styles:
                legend_items.append(Line2D([], [], color=_LINE_COLOR, linewidth=0.6, linestyle="-", label="Control"))
            if "--" in has_styles:
                legend_items.append(Line2D([], [], color=_LINE_COLOR, linewidth=0.6, linestyle="--", label="Readout Send"))
            if "-." in has_styles:
                legend_items.append(Line2D([], [], color=_LINE_COLOR, linewidth=0.6, linestyle="-.", label="Readout Return"))
            ax.legend(
                handles=legend_items, loc="upper right",
                fontsize=_FS_COMP, frameon=True, framealpha=0.9,
                edgecolor=_BAND_EDGE, fancybox=False,
            )

        ax.set_xlim(0, x_max)
        ax.set_ylim(y_bottom, y_top)
        ax.set_aspect("equal")
        ax.axis("off")

        output = Path(output)
        fig.savefig(output, bbox_inches="tight", dpi=300, facecolor="white")
        plt.close(fig)

    return output
