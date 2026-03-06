"""Programmatic generation of cooldown wiring configurations.

Two usage patterns:

1. **Template-based** — generates a cooldown directory from bundled templates::

    from cryo_wiring_core.builder import build_cooldown

    build_cooldown(
        output_dir="anemone/current",
        fridge="anemone",
        chip_name="sample-chip",
        num_qubits=16,
    )

2. **Model-based** — build from component objects (notebooks, scripts)::

    from cryo_wiring_core.builder import CooldownBuilder
    from cryo_wiring_core.models import Attenuator, Isolator, Amplifier, Stage

    cooldown = (
        CooldownBuilder(num_qubits=16)
        .control_module("my_ctrl", {
            Stage.K50: [Attenuator(model="XMA-10dB", value_dB=10)],
            Stage.K4: [Attenuator(model="XMA-20dB", value_dB=20)],
            Stage.MXC: [Attenuator(model="XMA-20dB", value_dB=20)],
        })
        .readout_send_module("my_rs", {
            Stage.K50: [Attenuator(model="XMA-10dB", value_dB=10)],
        })
        .readout_return_module("my_rr", {
            Stage.CP: [Isolator(model="LNF-ISC"), Isolator(model="LNF-ISC")],
            Stage.K50: [Amplifier(model="HEMT", amplifier_type="HEMT", gain_dB=40)],
        })
        .build()
    )

    # Rich result object
    cooldown.control          # WiringConfig
    cooldown.summary()        # print summary table
    cooldown.diagram("out.svg")
    cooldown.write("output/", fridge="anemone")

    # Bulk per-line overrides
    cooldown = (
        CooldownBuilder(num_qubits=8)
        .control_module("ctrl", {...})
        .for_lines("C00", "C03", "C05")
            .add(Stage.STILL, Filter(model="K&L", filter_type="Lowpass"))
            .remove(Stage.MXC, component_type="filter")
        .end()
        .build()
    )
"""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path
from typing import Sequence, Union

import yaml

from cryo_wiring_core.loader import (
    _resolve_components_in_stages,
    default_components_path,
    load_components,
    load_yaml,
    templates_dir,
)
from cryo_wiring_core.models import (
    Amplifier,
    Attenuator,
    ChipConfig,
    Component,
    ControlLine,
    CooldownMetadata,
    Filter,
    Isolator,
    ReadoutLine,
    Stage,
    WiringConfig,
)


def _id_width(n: int) -> int:
    """Minimum zero-padded width for 0..n-1."""
    return max(2, len(str(n - 1)))


def _dump_yaml(data: dict) -> str:
    """Serialize a dict to YAML with consistent formatting."""
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _component_to_dict(comp: Attenuator | Filter | Isolator | Amplifier) -> dict:
    """Serialize a component model to a plain dict for YAML output."""
    d = comp.model_dump(exclude_defaults=True)
    d["type"] = comp.type
    # Ensure 'type' appears first for readability
    return {"type": d.pop("type"), **d}


def _stages_to_dict(
    stages: dict[Stage, list[Attenuator | Filter | Isolator | Amplifier]],
) -> dict[str, list[dict]]:
    """Convert Stage-keyed component dict to YAML-friendly dict."""
    result: dict[str, list[dict]] = {}
    for stage, components in stages.items():
        result[stage.value] = [_component_to_dict(c) for c in components]
    return result


# -- Line generators --

def make_control_lines(num_qubits: int, module_name: str) -> list[dict]:
    """Generate control line definitions for *num_qubits* qubits."""
    w = _id_width(num_qubits)
    return [
        {"line_id": f"C{i:0{w}d}", "qubit": f"Q{i:0{w}d}", "module": module_name}
        for i in range(num_qubits)
    ]


def make_readout_send_lines(
    num_qubits: int,
    module_name: str,
    qubits_per_line: int = 4,
) -> list[dict]:
    """Generate readout-send line definitions."""
    n_readout = num_qubits // qubits_per_line
    qw = _id_width(num_qubits)
    rw = _id_width(n_readout)
    return [
        {
            "line_id": f"RS{i:0{rw}d}",
            "qubits": [f"Q{i * qubits_per_line + j:0{qw}d}" for j in range(qubits_per_line)],
            "module": module_name,
        }
        for i in range(n_readout)
    ]


def make_readout_return_lines(
    num_qubits: int,
    module_name: str,
    qubits_per_line: int = 4,
) -> list[dict]:
    """Generate readout-return line definitions."""
    n_readout = num_qubits // qubits_per_line
    qw = _id_width(num_qubits)
    rw = _id_width(n_readout)
    return [
        {
            "line_id": f"RR{i:0{rw}d}",
            "qubits": [f"Q{i * qubits_per_line + j:0{qw}d}" for j in range(qubits_per_line)],
            "module": module_name,
        }
        for i in range(n_readout)
    ]


def make_wiring_yaml(
    module_def: dict,
    module_name: str,
    lines: list[dict],
) -> dict:
    """Build a module-format wiring YAML dict."""
    return {"modules": {module_name: module_def}, "lines": lines}


# -- Cooldown result object --

LineIds = Union[str, Sequence[str]]

def _normalize_line_ids(line_ids: LineIds) -> list[str]:
    """Normalize a single line_id or sequence to a list."""
    if isinstance(line_ids, str):
        return [line_ids]
    return list(line_ids)


class Cooldown:
    """Result of ``CooldownBuilder.build()``.

    Provides attribute access, iteration (unpack), and convenience methods
    for summary / diagram / write.
    """

    __slots__ = ("control", "readout_send", "readout_return", "metadata", "_builder")

    def __init__(
        self,
        control: WiringConfig,
        readout_send: WiringConfig,
        readout_return: WiringConfig,
        builder: CooldownBuilder | None = None,
        metadata: CooldownMetadata | None = None,
    ) -> None:
        self.control = control
        self.readout_send = readout_send
        self.readout_return = readout_return
        self.metadata = metadata
        self._builder = builder

    # -- unpack support: control, rs, rr = cooldown --

    def __iter__(self):
        return iter((self.control, self.readout_send, self.readout_return))

    def __len__(self) -> int:
        return 3

    def __getitem__(self, index: int) -> WiringConfig:
        return (self.control, self.readout_send, self.readout_return)[index]

    # -- convenience methods --

    def summary(
        self,
        line_type: str = "all",
        fmt: str = "terminal",
        diagram: str | None = None,
    ) -> str | None:
        """Print or return a wiring summary.

        Parameters
        ----------
        fmt
            ``"terminal"`` (print via Rich), ``"markdown"``, or ``"html"``.
        diagram
            Relative path to a diagram image to embed (markdown only).
        """
        from cryo_wiring_core.summary import (
            generate_html_table,
            generate_markdown_table,
            print_summary,
        )

        if fmt == "terminal":
            print_summary(self.control, self.readout_send, self.readout_return, line_type=line_type, metadata=self.metadata)
            return None
        if fmt == "markdown":
            return generate_markdown_table(self.control, self.readout_send, self.readout_return, line_type=line_type, metadata=self.metadata, diagram=diagram)
        if fmt == "html":
            return generate_html_table(self.control, self.readout_send, self.readout_return, line_type=line_type, metadata=self.metadata)
        raise ValueError(f"Unknown format: {fmt!r}. Use 'terminal', 'markdown', or 'html'.")

    def diagram(
        self,
        output: str | Path = "wiring.svg",
        filter_lines: list[str] | None = None,
        representative: bool = False,
        width: float = 3.375,
    ) -> Path:
        """Generate a publication-quality wiring diagram."""
        from cryo_wiring_core.diagram import generate_diagram

        return generate_diagram(
            self.control,
            self.readout_send,
            self.readout_return,
            output=output,
            filter_lines=filter_lines,
            representative=representative,
            width=width,
            metadata=self.metadata,
        )

    def write(
        self,
        output_dir: str | Path,
        fridge: str,
        chip_name: str | None = None,
        cooldown_id: str = "cd001",
        cooldown_date: str | None = None,
        operator: str = "",
        purpose: str = "",
    ) -> Path:
        """Write the complete cooldown directory as YAML files."""
        if self._builder is None:
            raise RuntimeError("write() requires a builder reference. Use CooldownBuilder.build().")
        return self._builder.write(
            output_dir,
            fridge=fridge,
            chip_name=chip_name,
            cooldown_id=cooldown_id,
            cooldown_date=cooldown_date,
            operator=operator,
            purpose=purpose,
        )


# -- Scoped builder for bulk per-line overrides --

class _LineScope:
    """Scoped builder returned by ``CooldownBuilder.for_lines()``.

    Collects add/remove/replace operations for a fixed set of line IDs,
    then returns to the parent builder via ``.end()``.
    """

    def __init__(self, parent: CooldownBuilder, line_ids: list[str]) -> None:
        self._parent = parent
        self._line_ids = line_ids

    def add(
        self,
        stage: Stage,
        component: ComponentRef,
    ) -> _LineScope:
        """Add a component at *stage* on all scoped lines."""
        for lid in self._line_ids:
            self._parent.add(lid, stage, component)
        return self

    def remove(
        self,
        stage: Stage,
        *,
        component_type: str | None = None,
        index: int | None = None,
    ) -> _LineScope:
        """Remove component(s) at *stage* on all scoped lines."""
        for lid in self._line_ids:
            self._parent.remove(lid, stage, component_type=component_type, index=index)
        return self

    def replace(
        self,
        stage: Stage,
        index: int,
        component: ComponentRef,
    ) -> _LineScope:
        """Replace a component at *stage*/*index* on all scoped lines."""
        for lid in self._line_ids:
            self._parent.replace(lid, stage, index, component)
        return self

    def end(self) -> CooldownBuilder:
        """Return to the parent builder."""
        return self._parent


# -- Model-based builder --

ComponentRef = Union[Attenuator, Filter, Isolator, Amplifier, str]
ComponentList = list[ComponentRef]


class CooldownBuilder:
    """Fluent builder for constructing wiring configurations from component models.

    Example::

        cooldown = (
            CooldownBuilder(num_qubits=8)
            .control_module("ctrl", {
                Stage.K50: [Attenuator(model="XMA-10dB", value_dB=10)],
                Stage.MXC: [Attenuator(model="XMA-20dB", value_dB=20)],
            })
            .build()
        )
    """

    def __init__(
        self,
        num_qubits: int,
        qubits_per_readout_line: int = 4,
    ) -> None:
        self.num_qubits = num_qubits
        self.qubits_per_readout_line = qubits_per_readout_line
        self._catalog: dict[str, Attenuator | Filter | Isolator | Amplifier] = {}
        self._ctrl: tuple[str, dict[Stage, ComponentList]] | None = None
        self._rs: tuple[str, dict[Stage, ComponentList]] | None = None
        self._rr: tuple[str, dict[Stage, ComponentList]] | None = None
        self._overrides: list[tuple] = []
        self._fridge: str = ""
        self._chip_name: str = ""
        self._cooldown_id: str = "cd001"
        self._cooldown_date: str = ""
        self._operator: str = ""
        self._purpose: str = ""

    def component(
        self,
        key: str,
        comp: Attenuator | Filter | Isolator | Amplifier,
    ) -> CooldownBuilder:
        """Register a component in the catalog.

        Registered components can be referenced by *key* in module stage
        definitions and will be output as string references in YAML.
        """
        self._catalog[key] = comp
        return self

    def metadata(
        self,
        *,
        fridge: str = "",
        chip_name: str = "",
        cooldown_id: str = "cd001",
        cooldown_date: str = "",
        operator: str = "",
        purpose: str = "",
    ) -> CooldownBuilder:
        """Set metadata for the cooldown."""
        self._fridge = fridge
        self._chip_name = chip_name
        self._cooldown_id = cooldown_id
        self._cooldown_date = cooldown_date
        self._operator = operator
        self._purpose = purpose
        return self

    def control_module(
        self,
        name: str,
        stages: dict[Stage, ComponentList],
    ) -> CooldownBuilder:
        """Define the control module with components per stage."""
        self._ctrl = (name, stages)
        return self

    def readout_send_module(
        self,
        name: str,
        stages: dict[Stage, ComponentList],
    ) -> CooldownBuilder:
        """Define the readout-send module with components per stage."""
        self._rs = (name, stages)
        return self

    def readout_return_module(
        self,
        name: str,
        stages: dict[Stage, ComponentList],
    ) -> CooldownBuilder:
        """Define the readout-return module with components per stage."""
        self._rr = (name, stages)
        return self

    def for_lines(self, *line_ids: str) -> _LineScope:
        """Start a scoped builder for bulk overrides on the given lines.

        Example::

            builder.for_lines("C00", "C03", "C05")
                .add(Stage.STILL, Filter(model="K&L", filter_type="Lowpass"))
                .remove(Stage.MXC, component_type="filter")
            .end()
        """
        return _LineScope(self, list(line_ids))

    def add(
        self,
        line_ids: LineIds,
        stage: Stage,
        component: ComponentRef,
    ) -> CooldownBuilder:
        """Add a component to line(s) at a given stage.

        *component* can be a component object or a catalog key string::

            b.add("C00", Stage.STILL, "K&L-LPF")
            b.add("C00", Stage.STILL, Filter(model="K&L-5VLF", filter_type="Lowpass"))
        """
        for lid in _normalize_line_ids(line_ids):
            self._overrides.append(("add", lid, stage, component))
        return self

    def remove(
        self,
        line_ids: LineIds,
        stage: Stage,
        *,
        component_type: str | None = None,
        index: int | None = None,
    ) -> CooldownBuilder:
        """Remove component(s) from line(s) at a given stage.

        ``line_ids`` can be a single string or a list of strings.
        """
        for lid in _normalize_line_ids(line_ids):
            self._overrides.append(("remove", lid, stage, component_type, index))
        return self

    def replace(
        self,
        line_ids: LineIds,
        stage: Stage,
        index: int,
        component: ComponentRef,
    ) -> CooldownBuilder:
        """Replace a component at a specific position on line(s).

        *component* can be a component object or a catalog key string.
        """
        for lid in _normalize_line_ids(line_ids):
            self._overrides.append(("replace", lid, stage, index, component))
        return self

    def _apply_overrides(self, config: WiringConfig) -> None:
        """Apply per-line overrides to a built WiringConfig (in-place)."""
        line_map = {line.line_id: line for line in config.lines}
        for op in self._overrides:
            line = line_map.get(op[1])
            if line is None:
                continue
            stage: Stage = op[2]
            if op[0] == "add":
                line.stages.setdefault(stage, []).append(self._resolve_ref(op[3]))
            elif op[0] == "remove":
                comp_type, idx = op[3], op[4]
                comps = line.stages.get(stage, [])
                if idx is not None:
                    if 0 <= idx < len(comps):
                        comps.pop(idx)
                elif comp_type is not None:
                    for i, c in enumerate(comps):
                        if c.type == comp_type:
                            comps.pop(i)
                            break
                else:
                    line.stages[stage] = []
            elif op[0] == "replace":
                idx, comp = op[3], op[4]
                comps = line.stages.get(stage, [])
                if 0 <= idx < len(comps):
                    comps[idx] = self._resolve_ref(comp)

    def _resolve_ref(self, ref: ComponentRef) -> Attenuator | Filter | Isolator | Amplifier:
        """Resolve a component reference (key string or object) to a component."""
        if isinstance(ref, str):
            if ref not in self._catalog:
                raise ValueError(f"Unknown component key: {ref!r}. Register it with .component() first.")
            return self._catalog[ref]
        return ref

    def _resolve_stages(self, stages: dict[Stage, ComponentList]) -> dict[Stage, list[Attenuator | Filter | Isolator | Amplifier]]:
        """Resolve all component refs in a stage dict to concrete objects."""
        return {stage: [self._resolve_ref(c) for c in comps] for stage, comps in stages.items()}

    def _build_wiring_config(
        self,
        module_name: str,
        stages: dict[Stage, ComponentList],
        lines_dicts: list[dict],
    ) -> WiringConfig:
        """Build a WiringConfig from a module definition and line dicts."""
        resolved = self._resolve_stages(stages)
        parsed_lines: list[ControlLine | ReadoutLine] = []
        for line_dict in lines_dicts:
            line_id = line_dict["line_id"]
            line_stages = copy.deepcopy(resolved)
            if line_id.startswith("C"):
                parsed_lines.append(ControlLine(
                    line_id=line_id,
                    qubit=line_dict["qubit"],
                    stages=line_stages,
                ))
            else:
                parsed_lines.append(ReadoutLine(
                    line_id=line_id,
                    qubits=line_dict["qubits"],
                    stages=line_stages,
                ))
        return WiringConfig(lines=parsed_lines)

    def build(self) -> Cooldown:
        """Build a :class:`Cooldown` result object.

        The result supports unpacking::

            control, readout_send, readout_return = builder.build()

        And attribute access with convenience methods::

            cooldown = builder.build()
            cooldown.control
            cooldown.summary()
            cooldown.diagram("out.svg")
        """
        if self._ctrl is None:
            raise ValueError("Control module not defined. Call control_module() first.")

        ctrl_name, ctrl_stages = self._ctrl
        ctrl_lines = make_control_lines(self.num_qubits, ctrl_name)
        control = self._build_wiring_config(ctrl_name, ctrl_stages, ctrl_lines)

        if self._rs is not None:
            rs_name, rs_stages = self._rs
            rs_lines = make_readout_send_lines(self.num_qubits, rs_name, self.qubits_per_readout_line)
            readout_send = self._build_wiring_config(rs_name, rs_stages, rs_lines)
        else:
            readout_send = WiringConfig(lines=[])

        if self._rr is not None:
            rr_name, rr_stages = self._rr
            rr_lines = make_readout_return_lines(self.num_qubits, rr_name, self.qubits_per_readout_line)
            readout_return = self._build_wiring_config(rr_name, rr_stages, rr_lines)
        else:
            readout_return = WiringConfig(lines=[])

        for cfg in (control, readout_send, readout_return):
            self._apply_overrides(cfg)

        meta = None
        if self._fridge or self._chip_name:
            d = self._cooldown_date or date.today().isoformat()
            meta = CooldownMetadata(
                cooldown_id=self._cooldown_id,
                date=d,
                fridge=self._fridge,
                operator=self._operator,
                purpose=self._purpose,
            )

        return Cooldown(control, readout_send, readout_return, builder=self, metadata=meta)

    def _component_ref_to_yaml(self, ref: ComponentRef) -> str | dict:
        """Serialize a component ref to YAML: string key or inline dict."""
        if isinstance(ref, str):
            return ref
        return _component_to_dict(ref)

    def _stages_to_yaml_dict(self, stages: dict[Stage, ComponentList]) -> dict[str, list[str | dict]]:
        """Convert Stage-keyed component list to YAML-friendly dict, preserving key refs."""
        result: dict[str, list[str | dict]] = {}
        for stage, components in stages.items():
            result[stage.value] = [self._component_ref_to_yaml(c) for c in components]
        return result

    def _overrides_for_line(self, line_id: str, module_stages: dict[Stage, ComponentList]) -> dict[str, dict] | None:
        """Build spec-format stage overrides dict for a single line.

        Returns ``None`` if the line has no overrides.
        """
        # Collect per-stage add/remove lists
        stage_adds: dict[Stage, list] = {}
        stage_removes: dict[Stage, list] = {}

        for op in self._overrides:
            if op[1] != line_id:
                continue
            if op[0] == "add":
                _, _, stage, comp = op
                stage_adds.setdefault(stage, []).append(comp)
            elif op[0] == "remove":
                _, _, stage, comp_type, idx = op
                mod_comps = module_stages.get(stage, [])
                if idx is not None and 0 <= idx < len(mod_comps):
                    target = mod_comps[idx]
                    # Use key string if catalog ref, else {"model": ...}
                    if isinstance(target, str):
                        stage_removes.setdefault(stage, []).append(target)
                    else:
                        stage_removes.setdefault(stage, []).append({"model": target.model})
                elif comp_type is not None:
                    for ref in mod_comps:
                        resolved = self._resolve_ref(ref) if isinstance(ref, str) else ref
                        if resolved.type == comp_type:
                            if isinstance(ref, str):
                                stage_removes.setdefault(stage, []).append(ref)
                            else:
                                stage_removes.setdefault(stage, []).append({"model": resolved.model})
                            break
            elif op[0] == "replace":
                _, _, stage, idx, new_comp = op
                mod_comps = module_stages.get(stage, [])
                if 0 <= idx < len(mod_comps):
                    target = mod_comps[idx]
                    if isinstance(target, str):
                        stage_removes.setdefault(stage, []).append(target)
                    else:
                        stage_removes.setdefault(stage, []).append({"model": target.model})
                    stage_adds.setdefault(stage, []).append(new_comp)

        if not stage_adds and not stage_removes:
            return None

        result: dict[str, dict] = {}
        all_stages = set(stage_adds) | set(stage_removes)
        for stage in all_stages:
            override: dict[str, list] = {}
            if stage in stage_removes:
                override["remove"] = stage_removes[stage]
            if stage in stage_adds:
                override["add"] = [
                    self._component_ref_to_yaml(c) for c in stage_adds[stage]
                ]
            result[stage.value] = override
        return result

    def _apply_overrides_to_lines(self, lines_dicts: list[dict], module_stages: dict[Stage, ComponentList]) -> list[dict]:
        """Inject spec-format stage overrides into line dicts."""
        result = []
        for line_dict in lines_dicts:
            d = dict(line_dict)
            overrides = self._overrides_for_line(d["line_id"], module_stages)
            if overrides:
                d["stages"] = overrides
            result.append(d)
        return result

    def _module_to_yaml_dict(
        self,
        name: str,
        stages: dict[Stage, ComponentList],
        lines_dicts: list[dict],
    ) -> dict:
        """Serialize a module + lines to a YAML-ready dict."""
        module_def = {"stages": self._stages_to_yaml_dict(stages)}
        lines_with_overrides = self._apply_overrides_to_lines(lines_dicts, stages)
        return make_wiring_yaml(module_def, name, lines_with_overrides)

    def write(
        self,
        output_dir: str | Path,
        fridge: str,
        chip_name: str | None = None,
        cooldown_id: str = "cd001",
        cooldown_date: str | None = None,
        operator: str = "",
        purpose: str = "",
    ) -> Path:
        """Write the complete cooldown directory as YAML files."""
        if self._ctrl is None:
            raise ValueError("Control module not defined. Call control_module() first.")

        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        d = cooldown_date or date.today().isoformat()
        cname = chip_name or f"chip-{self.num_qubits}q"

        # metadata.yaml
        meta = CooldownMetadata(
            cooldown_id=cooldown_id,
            date=d,
            fridge=fridge,
            operator=operator,
            purpose=purpose,
        )
        (output / "metadata.yaml").write_text(
            _dump_yaml(meta.model_dump(exclude_defaults=True))
        )

        # chip.yaml
        chip = ChipConfig(name=cname, num_qubits=self.num_qubits)
        (output / "chip.yaml").write_text(
            _dump_yaml(chip.model_dump())
        )

        # components.yaml (if catalog is non-empty)
        if self._catalog:
            catalog_data = {
                key: _component_to_dict(comp)
                for key, comp in self._catalog.items()
            }
            (output / "components.yaml").write_text(_dump_yaml(catalog_data))

        # control.yaml
        ctrl_name, ctrl_stages = self._ctrl
        ctrl_lines = make_control_lines(self.num_qubits, ctrl_name)
        (output / "control.yaml").write_text(
            _dump_yaml(self._module_to_yaml_dict(ctrl_name, ctrl_stages, ctrl_lines))
        )

        # readout_send.yaml
        if self._rs is not None:
            rs_name, rs_stages = self._rs
            rs_lines = make_readout_send_lines(self.num_qubits, rs_name, self.qubits_per_readout_line)
            (output / "readout_send.yaml").write_text(
                _dump_yaml(self._module_to_yaml_dict(rs_name, rs_stages, rs_lines))
            )

        # readout_return.yaml
        if self._rr is not None:
            rr_name, rr_stages = self._rr
            rr_lines = make_readout_return_lines(self.num_qubits, rr_name, self.qubits_per_readout_line)
            (output / "readout_return.yaml").write_text(
                _dump_yaml(self._module_to_yaml_dict(rr_name, rr_stages, rr_lines))
            )

        return output


# -- Template-based builder --

def _load_module_template(
    template_filename: str,
    catalog: dict,
) -> tuple[str, dict]:
    """Load a module template and resolve component references.

    Returns (module_name, resolved_module_def).
    """
    data = load_yaml(templates_dir() / template_filename)
    name = next(iter(data))
    module_def = data[name]
    module_def["stages"] = _resolve_components_in_stages(module_def["stages"], catalog)
    return name, module_def


def build_cooldown(
    output_dir: str | Path,
    fridge: str,
    chip_name: str,
    num_qubits: int,
    cooldown_id: str = "cd001",
    cooldown_date: str | None = None,
    operator: str = "",
    purpose: str = "",
    components_path: Path | None = None,
) -> Path:
    """Generate a complete cooldown directory from bundled templates.

    Parameters
    ----------
    output_dir
        Directory to create.
    fridge
        Fridge name (e.g. ``"anemone"``).
    chip_name
        Chip name for ``chip.yaml``.
    num_qubits
        Number of qubits.
    cooldown_id
        Cooldown identifier (e.g. ``"cd001"``).
    cooldown_date
        Date string (``YYYY-MM-DD``). Defaults to today.
    operator
        Operator name.
    purpose
        Purpose description.
    components_path
        Path to a custom components catalog.  Defaults to the bundled catalog.

    Returns
    -------
    Path
        The output directory.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    d = cooldown_date or date.today().isoformat()

    # metadata.yaml
    meta_template = templates_dir() / "metadata.yaml"
    content = meta_template.read_text()
    content = (
        content
        .replace("cdNNN", cooldown_id)
        .replace("YYYY-MM-DD", d)
        .replace("FRIDGE", fridge)
    )
    if operator:
        content = content.replace('operator: ""', f'operator: "{operator}"')
    if purpose:
        content = content.replace('purpose: ""', f'purpose: "{purpose}"')
    (output / "metadata.yaml").write_text(content)

    # chip.yaml
    chip_data = {"name": chip_name, "num_qubits": num_qubits}
    (output / "chip.yaml").write_text(_dump_yaml(chip_data))

    # Load component catalog
    comp_path = components_path or default_components_path()
    catalog = load_components(comp_path)

    # Control
    ctrl_name, ctrl_def = _load_module_template("control_module.yaml", catalog)
    ctrl_lines = make_control_lines(num_qubits, ctrl_name)
    (output / "control.yaml").write_text(
        _dump_yaml(make_wiring_yaml(ctrl_def, ctrl_name, ctrl_lines))
    )

    # Readout send
    rs_name, rs_def = _load_module_template("readout_send_module.yaml", catalog)
    rs_lines = make_readout_send_lines(num_qubits, rs_name)
    (output / "readout_send.yaml").write_text(
        _dump_yaml(make_wiring_yaml(rs_def, rs_name, rs_lines))
    )

    # Readout return
    rr_name, rr_def = _load_module_template("readout_return_module.yaml", catalog)
    rr_lines = make_readout_return_lines(num_qubits, rr_name)
    (output / "readout_return.yaml").write_text(
        _dump_yaml(make_wiring_yaml(rr_def, rr_name, rr_lines))
    )

    return output
