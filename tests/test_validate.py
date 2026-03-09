"""Tests for cryo_wiring_core validation."""

import pytest
from jsonschema import ValidationError

from cryo_wiring_core import validate_chip, validate_components, validate_metadata, validate_wiring


class TestValidateWiring:
    def test_valid_flat_format(self):
        data = {
            "lines": [
                {
                    "line_id": "C00",
                    "qubit": "Q00",
                    "stages": {
                        "RT": [
                            {"type": "attenuator", "manufacturer": "XMA", "model": "10dB", "value_dB": 10}
                        ],
                        "MXC": [
                            {"type": "filter", "manufacturer": "XMA", "model": "Ecco", "filter_type": "Eccosorb"}
                        ],
                    },
                }
            ]
        }
        validate_wiring(data)

    def test_valid_module_format(self):
        data = {
            "modules": {
                "control_standard": {
                    "stages": {
                        "50K": ["XMA-10dB"],
                        "4K": ["XMA-20dB"],
                    }
                }
            },
            "lines": [
                {"line_id": "C00", "qubit": "Q00", "module": "control_standard"}
            ],
        }
        validate_wiring(data)

    def test_valid_module_with_override(self):
        data = {
            "modules": {
                "control_standard": {
                    "stages": {"4K": ["XMA-20dB"]}
                }
            },
            "lines": [
                {
                    "line_id": "C01",
                    "qubit": "Q01",
                    "module": "control_standard",
                    "stages": {
                        "4K": {"add": ["LPF-KL"], "remove": ["XMA-20dB"]}
                    },
                }
            ],
        }
        validate_wiring(data)

    def test_valid_readout_send_line(self):
        data = {
            "lines": [
                {
                    "line_id": "RS00",
                    "qubits": ["Q00", "Q01", "Q02", "Q03"],
                    "stages": {"MXC": ["Eccosorb"]},
                }
            ]
        }
        validate_wiring(data)

    def test_valid_readout_return_line(self):
        data = {
            "lines": [
                {
                    "line_id": "RR00",
                    "qubits": ["Q00", "Q01", "Q02", "Q03"],
                    "stages": {
                        "4K": [
                            {"type": "amplifier", "manufacturer": "LNF", "model": "LNC4_8C", "amplifier_type": "HEMT", "gain_dB": 38}
                        ]
                    },
                }
            ]
        }
        validate_wiring(data)

    def test_invalid_line_id_prefix(self):
        data = {
            "lines": [
                {"line_id": "X00", "qubit": "Q00", "stages": {"RT": []}}
            ]
        }
        with pytest.raises(ValidationError):
            validate_wiring(data)

    def test_invalid_stage_name(self):
        data = {
            "lines": [
                {"line_id": "C00", "qubit": "Q00", "stages": {"300K": []}}
            ]
        }
        with pytest.raises(ValidationError):
            validate_wiring(data)

    def test_missing_lines(self):
        with pytest.raises(ValidationError):
            validate_wiring({"modules": {}})

    def test_line_requires_stages_or_module(self):
        data = {"lines": [{"line_id": "C00", "qubit": "Q00"}]}
        with pytest.raises(ValidationError):
            validate_wiring(data)


class TestValidateMetadata:
    def test_valid_metadata(self):
        data = {
            "cooldown_id": "cd001",
            "date": "2026-03-01",
            "cryo": "BlueFors-LD400",
            "operator": "Alice",
            "purpose": "Qubit characterization",
            "notes": "Test run",
        }
        validate_metadata(data)

    def test_minimal_metadata(self):
        data = {
            "cooldown_id": "cd001",
            "date": "2026-03-01",
            "cryo": "BlueFors-LD400",
        }
        validate_metadata(data)

    def test_invalid_cooldown_id(self):
        data = {
            "cooldown_id": "xyz",
            "date": "2026-03-01",
            "cryo": "BlueFors-LD400",
        }
        with pytest.raises(ValidationError):
            validate_metadata(data)

    def test_missing_required_field(self):
        data = {"cooldown_id": "cd001", "date": "2026-03-01"}
        with pytest.raises(ValidationError):
            validate_metadata(data)

    def test_additional_properties_rejected(self):
        data = {
            "cooldown_id": "cd001",
            "date": "2026-03-01",
            "cryo": "BlueFors-LD400",
            "unknown_field": "value",
        }
        with pytest.raises(ValidationError):
            validate_metadata(data)

    def test_cooldown_id_allows_more_than_three_digits(self):
        data = {
            "cooldown_id": "cd1000",
            "date": "2026-03-01",
            "cryo": "BlueFors-LD400",
        }
        validate_metadata(data)


class TestValidateComponents:
    def test_valid_attenuator(self):
        data = {
            "XMA-10dB": {
                "type": "attenuator",
                "manufacturer": "XMA",
                "model": "2002-6210-10",
                "value_dB": 10,
            }
        }
        validate_components(data)

    def test_valid_filter(self):
        data = {
            "Eccosorb": {
                "type": "filter",
                "manufacturer": "XMA",
                "model": "CR110",
                "filter_type": "Eccosorb",
            }
        }
        validate_components(data)

    def test_valid_isolator(self):
        data = {
            "ISO-1": {
                "type": "isolator",
                "manufacturer": "LNF",
                "model": "ISC4_12A",
                "serial": "SN001",
            }
        }
        validate_components(data)

    def test_valid_amplifier(self):
        data = {
            "HEMT-1": {
                "type": "amplifier",
                "manufacturer": "LNF",
                "model": "LNC4_8C",
                "amplifier_type": "HEMT",
                "gain_dB": 38,
            }
        }
        validate_components(data)

    def test_missing_type(self):
        data = {"comp1": {"manufacturer": "XMA", "model": "ABC"}}
        with pytest.raises(ValidationError):
            validate_components(data)

    def test_missing_manufacturer(self):
        data = {"comp1": {"type": "attenuator", "model": "ABC"}}
        with pytest.raises(ValidationError):
            validate_components(data)

    def test_missing_model(self):
        data = {"comp1": {"type": "attenuator", "manufacturer": "XMA"}}
        with pytest.raises(ValidationError):
            validate_components(data)

    def test_invalid_type(self):
        data = {"comp1": {"type": "cable", "manufacturer": "XMA", "model": "ABC"}}
        with pytest.raises(ValidationError):
            validate_components(data)

    def test_additional_properties_rejected(self):
        data = {
            "comp1": {
                "type": "attenuator",
                "manufacturer": "XMA",
                "model": "ABC",
                "unknown": "value",
            }
        }
        with pytest.raises(ValidationError):
            validate_components(data)


class TestValidateChip:
    def test_valid_chip(self):
        data = {"name": "TestChip-64Q", "num_qubits": 64}
        validate_chip(data)

    def test_minimal_chip(self):
        data = {"name": "Chip1", "num_qubits": 1}
        validate_chip(data)

    def test_missing_name(self):
        data = {"num_qubits": 64}
        with pytest.raises(ValidationError):
            validate_chip(data)

    def test_missing_num_qubits(self):
        data = {"name": "Chip1"}
        with pytest.raises(ValidationError):
            validate_chip(data)

    def test_num_qubits_minimum(self):
        data = {"name": "Chip1", "num_qubits": 0}
        with pytest.raises(ValidationError):
            validate_chip(data)

    def test_additional_properties_rejected(self):
        data = {"name": "Chip1", "num_qubits": 64, "unknown": "value"}
        with pytest.raises(ValidationError):
            validate_chip(data)
