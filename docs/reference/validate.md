# Validate

::: cryo_wiring_core.validate

## Functions

| Function | Description |
| --- | --- |
| `validate_wiring(data)` | Validate control/readout YAML against schema |
| `validate_metadata(data)` | Validate metadata YAML against schema |
| `validate_components(data)` | Validate components YAML against schema |
| `validate_chip(data)` | Validate chip YAML against schema |

All functions raise `jsonschema.ValidationError` on failure.
