"""End-to-end roundtrip tests: JSON Schema validation -> expand -> Pydantic parsing.

These tests ensure that JSON Schema and Pydantic models stay in sync.
Sample data that passes JSON Schema validation must also be parseable by Pydantic,
and vice versa.
"""

import pytest
from jsonschema import ValidationError

from cryo_wiring_core import (
    validate_chip,
    validate_components,
    validate_metadata,
    validate_wiring,
    expand_modules,
    ChipConfig,
    CooldownMetadata,
    WiringConfig,
    ControlLine,
    ReadoutLine,
    Attenuator,
    Filter,
    Isolator,
    Amplifier,
    Stage,
)


# -- Sample data matching both schema and model --

SAMPLE_METADATA = {
    "cooldown_id": "cd001",
    "date": "2026-03-01",
    "cryo": "BlueFors-LD400",
    "operator": "Alice",
    "purpose": "Qubit characterization",
    "notes": "Initial run",
}

SAMPLE_CHIP = {
    "name": "TestChip-64Q",
    "num_qubits": 64,
}

SAMPLE_COMPONENTS = {
    "XMA-10dB": {
        "type": "attenuator",
        "manufacturer": "XMA",
        "model": "2082-6431-10",
        "value_dB": 10,
    },
    "XMA-20dB": {
        "type": "attenuator",
        "manufacturer": "XMA",
        "model": "2082-6431-20",
        "value_dB": 20,
    },
    "LPF-KL": {
        "type": "filter",
        "manufacturer": "K&L",
        "model": "6L250-12000",
        "filter_type": "Lowpass",
    },
    "Eccosorb": {
        "type": "filter",
        "manufacturer": "XMA",
        "model": "EF-03",
        "filter_type": "Eccosorb",
    },
    "ISO-LNF": {
        "type": "isolator",
        "manufacturer": "LNF",
        "model": "ISC4_12A",
    },
    "HEMT-LNF": {
        "type": "amplifier",
        "manufacturer": "LNF",
        "model": "LNC03_14A",
        "amplifier_type": "HEMT",
        "gain_dB": 40,
    },
}

SAMPLE_WIRING_FLAT = {
    "lines": [
        {
            "line_id": "C00",
            "qubit": "Q00",
            "stages": {
                "50K": [
                    {"type": "attenuator", "manufacturer": "XMA", "model": "2082-6431-10", "value_dB": 10}
                ],
                "4K": [
                    {"type": "attenuator", "manufacturer": "XMA", "model": "2082-6431-20", "value_dB": 20}
                ],
                "MXC": [
                    {"type": "attenuator", "manufacturer": "XMA", "model": "2082-6431-20", "value_dB": 20},
                    {"type": "filter", "manufacturer": "XMA", "model": "EF-03", "filter_type": "Eccosorb"},
                ],
            },
        },
        {
            "line_id": "RS00",
            "qubits": ["Q00", "Q01", "Q02", "Q03"],
            "stages": {
                "50K": [
                    {"type": "attenuator", "manufacturer": "XMA", "model": "2082-6431-10", "value_dB": 10}
                ],
            },
        },
        {
            "line_id": "RR00",
            "qubits": ["Q00", "Q01", "Q02", "Q03"],
            "stages": {
                "CP": [
                    {"type": "isolator", "manufacturer": "LNF", "model": "ISC4_12A"},
                ],
                "50K": [
                    {"type": "amplifier", "manufacturer": "LNF", "model": "LNC03_14A", "amplifier_type": "HEMT", "gain_dB": 40},
                ],
            },
        },
    ]
}

SAMPLE_WIRING_MODULE = {
    "modules": {
        "control_standard": {
            "stages": {
                "50K": ["XMA-10dB"],
                "4K": ["XMA-20dB"],
                "MXC": ["XMA-20dB"],
            }
        }
    },
    "lines": [
        {
            "line_id": "C00",
            "qubit": "Q00",
            "module": "control_standard",
            "stages": {
                "MXC": {
                    "add": ["Eccosorb"],
                },
            },
        },
        {
            "line_id": "C01",
            "qubit": "Q01",
            "module": "control_standard",
        },
    ],
}


class TestMetadataRoundtrip:
    """Metadata: JSON Schema <-> Pydantic consistency."""

    def test_valid_data_passes_both(self):
        validate_metadata(SAMPLE_METADATA)
        meta = CooldownMetadata.model_validate(SAMPLE_METADATA)
        assert meta.cooldown_id == "cd001"
        assert meta.cryo == "BlueFors-LD400"

    def test_cryo_required_in_both(self):
        data = {"cooldown_id": "cd001", "date": "2026-03-01"}
        with pytest.raises(ValidationError):
            validate_metadata(data)
        with pytest.raises(Exception):  # pydantic ValidationError
            CooldownMetadata.model_validate(data)

    def test_cooldown_id_pattern_in_both(self):
        data = {**SAMPLE_METADATA, "cooldown_id": "xyz"}
        with pytest.raises(ValidationError):
            validate_metadata(data)
        with pytest.raises(Exception):  # pydantic ValidationError
            CooldownMetadata.model_validate(data)

    def test_minimal_metadata(self):
        data = {"cooldown_id": "cd001", "date": "2026-03-01", "cryo": "test"}
        validate_metadata(data)
        meta = CooldownMetadata.model_validate(data)
        assert meta.operator == ""


class TestChipRoundtrip:
    """Chip: JSON Schema <-> Pydantic consistency."""

    def test_valid_data_passes_both(self):
        validate_chip(SAMPLE_CHIP)
        chip = ChipConfig.model_validate(SAMPLE_CHIP)
        assert chip.num_qubits == 64

    def test_num_qubits_field_name(self):
        """Both schema and model use num_qubits (not n_qubits)."""
        data = {"name": "Chip", "n_qubits": 8}
        with pytest.raises(ValidationError):
            validate_chip(data)
        with pytest.raises(Exception):
            ChipConfig.model_validate(data)

    def test_num_qubits_minimum(self):
        data = {"name": "Chip", "num_qubits": 0}
        with pytest.raises(ValidationError):
            validate_chip(data)
        with pytest.raises(Exception):
            ChipConfig.model_validate(data)


class TestComponentsRoundtrip:
    """Components: JSON Schema validation of catalog data."""

    def test_valid_catalog(self):
        validate_components(SAMPLE_COMPONENTS)


class TestWiringRoundtrip:
    """Wiring: JSON Schema -> expand_modules -> Pydantic."""

    def test_flat_format_end_to_end(self):
        validate_wiring(SAMPLE_WIRING_FLAT)
        config = WiringConfig.from_raw(SAMPLE_WIRING_FLAT)
        assert len(config.lines) == 3
        assert isinstance(config.lines[0], ControlLine)
        assert isinstance(config.lines[1], ReadoutLine)
        assert isinstance(config.lines[2], ReadoutLine)

    def test_module_format_end_to_end(self):
        """Module format -> schema validation -> expand -> Pydantic."""
        validate_wiring(SAMPLE_WIRING_MODULE)
        expanded = expand_modules(SAMPLE_WIRING_MODULE, SAMPLE_COMPONENTS)
        config = WiringConfig.from_raw(expanded)
        assert len(config.lines) == 2

        c00 = config.lines[0]
        assert isinstance(c00, ControlLine)
        assert c00.line_id == "C00"
        # C00 has MXC override: add Eccosorb
        mxc_comps = c00.stages[Stage.MXC]
        assert len(mxc_comps) == 2  # XMA-20dB + Eccosorb
        assert isinstance(mxc_comps[0], Attenuator)
        assert isinstance(mxc_comps[1], Filter)

        c01 = config.lines[1]
        assert isinstance(c01, ControlLine)
        # C01 uses module as-is
        assert len(c01.stages[Stage.MXC]) == 1

    def test_component_types_parsed_correctly(self):
        """All component types survive the roundtrip."""
        config = WiringConfig.from_raw(SAMPLE_WIRING_FLAT)
        c00 = config.lines[0]
        assert isinstance(c00.stages[Stage.K50][0], Attenuator)
        assert isinstance(c00.stages[Stage.MXC][1], Filter)

        rr00 = config.lines[2]
        assert isinstance(rr00.stages[Stage.CP][0], Isolator)
        assert isinstance(rr00.stages[Stage.K50][0], Amplifier)

    def test_expand_with_add_remove(self):
        """Module override add/remove -> expanded flat -> Pydantic."""
        data = {
            "modules": {
                "mod": {
                    "stages": {
                        "4K": ["XMA-20dB"],
                        "MXC": ["XMA-20dB"],
                    }
                }
            },
            "lines": [
                {
                    "line_id": "C00",
                    "qubit": "Q00",
                    "module": "mod",
                    "stages": {
                        "MXC": {
                            "remove": ["XMA-20dB"],
                            "add": ["XMA-10dB"],
                        }
                    },
                }
            ],
        }
        validate_wiring(data)
        expanded = expand_modules(data, SAMPLE_COMPONENTS)
        config = WiringConfig.from_raw(expanded)
        c00 = config.lines[0]
        assert len(c00.stages[Stage.MXC]) == 1
        assert isinstance(c00.stages[Stage.MXC][0], Attenuator)
        assert c00.stages[Stage.MXC][0].value_dB == 10
