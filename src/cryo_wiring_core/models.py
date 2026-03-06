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


class Attenuator(BaseModel):
    type: Literal["attenuator"] = "attenuator"
    model: str
    serial: str = ""
    value_dB: float = 0.0


class Filter(BaseModel):
    type: Literal["filter"] = "filter"
    model: str
    serial: str = ""
    filter_type: str = ""


class Isolator(BaseModel):
    type: Literal["isolator"] = "isolator"
    model: str
    serial: str = ""


class Amplifier(BaseModel):
    type: Literal["amplifier"] = "amplifier"
    model: str
    serial: str = ""
    amplifier_type: str = ""
    gain_dB: float = 0.0


Component = Annotated[
    Union[Attenuator, Filter, Isolator, Amplifier],
    Field(discriminator="type"),
]


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
