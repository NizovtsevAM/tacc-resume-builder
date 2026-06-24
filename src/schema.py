"""
JSON Schema validation for input/tacc.json.
"""

TACC_SCHEMA = {
    "type": "object",
    "required": [],
    "properties": {
        "records": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [],
                "properties": {
                    "CustomerName": {"type": "string"},
                    "Date": {"type": "string"},
                    "Description": {"type": ["string", "null"]},
                    "ContractId": {"type": ["integer", "null", "string"]},
                    "Hours": {"type": ["number", "integer", "null"]},
                },
            },
        }
    },
}

INPUT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": [],
        "properties": {
            "CustomerName": {"type": "string"},
            "Date": {"type": "string"},
            "Description": {"type": ["string", "null"]},
            "ContractId": {"type": ["integer", "null", "string"]},
            "Hours": {"type": ["number", "integer", "null"]},
        },
    },
}


def validate_tacc_data(data: object) -> None:
    """Validate TACC JSON data structure. Raises ValueError on invalid schema."""
    try:
        import jsonschema
    except ImportError:
        return

    schemas = [TACC_SCHEMA, INPUT_SCHEMA]
    for schema in schemas:
        try:
            jsonschema.validate(data, schema)
            return
        except jsonschema.ValidationError:
            continue
    raise ValueError("Invalid TACC data schema: unknown structure")
