"""Pydantic v2 data models for dilution refrigerator wiring configuration."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class Stage(str, Enum):
    RT = "RT"
    K50 = "50K"
    K4 = "4K"
    STILL = "Still"
    CP = "CP"
    MXC = "MXC"


STAGE_ORDER = [Stage.RT, Stage.K50, Stage.K4, Stage.STILL, Stage.CP, Stage.MXC]


# -- Component models --


class _ComponentBase(BaseModel):
    """Common fields shared by all component types."""

    manufacturer: str
    model: str
    serial: str = ""

    @property
    def label(self) -> str:
        """Short display label for wiring diagrams."""
        return "?"

    @property
    def summary_label(self) -> str:
        """Descriptive label for summary tables."""
        return self.label

    @property
    def attenuation(self) -> float:
        """Attenuation contributed by this component (dB). Override in subclasses."""
        return 0.0

    @property
    def gain(self) -> float:
        """Gain contributed by this component (dB). Override in subclasses."""
        return 0.0


class Attenuator(_ComponentBase):
    type: Literal["attenuator"] = "attenuator"
    value_dB: float = 0.0

    @property
    def label(self) -> str:
        return f"{self.value_dB:.0f} dB"

    @property
    def summary_label(self) -> str:
        return f"ATT {self.value_dB:.0f}dB"

    @property
    def attenuation(self) -> float:
        return self.value_dB


class Filter(_ComponentBase):
    type: Literal["filter"] = "filter"
    filter_type: str = ""

    @property
    def label(self) -> str:
        if self.filter_type:
            name = self.filter_type
            return "Ecco." if name.lower().startswith("ecco") else name[:5]
        return "FLT"

    @property
    def summary_label(self) -> str:
        return self.filter_type or "filter"


class Isolator(_ComponentBase):
    type: Literal["isolator"] = "isolator"

    @property
    def label(self) -> str:
        return "ISO"

    @property
    def summary_label(self) -> str:
        return "ISO"


class Amplifier(_ComponentBase):
    type: Literal["amplifier"] = "amplifier"
    amplifier_type: str = ""
    gain_dB: float = 0.0

    @property
    def label(self) -> str:
        return f"+{self.gain_dB:.0f} dB"

    @property
    def summary_label(self) -> str:
        at = self.amplifier_type or "AMP"
        return f"{at} +{self.gain_dB:.0f}dB"

    @property
    def gain(self) -> float:
        return self.gain_dB


class CustomComponent(_ComponentBase):
    """User-defined component (DC block, mixer, switch, etc.)."""

    type: Literal["custom"] = "custom"
    custom_type: str = ""

    @property
    def label(self) -> str:
        return self.custom_type or self.model

    @property
    def summary_label(self) -> str:
        return self.custom_type or self.model


Component = Annotated[
    Union[Attenuator, Filter, Isolator, Amplifier, CustomComponent],
    Field(discriminator="type"),
]


# -- Line & config models --


class ControlLine(BaseModel):
    line_id: str = Field(pattern=r"^C\d+$")
    qubit: str = Field(pattern=r"^Q\d+$")
    stages: dict[Stage, list[Component]] = Field(default_factory=dict)


class ReadoutLine(BaseModel):
    line_id: str = Field(pattern=r"^(RS|RR)\d+$")
    qubits: list[str]
    stages: dict[Stage, list[Component]] = Field(default_factory=dict)


class WiringConfig(BaseModel):
    lines: list[ControlLine | ReadoutLine]

    @classmethod
    def from_raw(cls, data: dict) -> WiringConfig:
        """Parse raw YAML dict, dispatching lines by C/RS/RR prefix."""
        parsed_lines: list[ControlLine | ReadoutLine] = []
        for line_data in data.get("lines", []):
            line_id = line_data.get("line_id", "")
            if line_id.startswith("C"):
                parsed_lines.append(ControlLine.model_validate(line_data))
            elif line_id.startswith("RS") or line_id.startswith("RR"):
                parsed_lines.append(ReadoutLine.model_validate(line_data))
            else:
                raise ValueError(f"Unknown line_id prefix: {line_id}")
        return cls(lines=parsed_lines)


class CooldownMetadata(BaseModel):
    cooldown_id: str = Field(pattern=r"^cd\d{3,}$")
    date: str
    fridge: str
    operator: str = ""
    purpose: str = ""
    notes: str = ""


class ChipConfig(BaseModel):
    name: str
    num_qubits: int = Field(ge=1)
    qubits_per_readout_line: int = Field(default=4, ge=1)
