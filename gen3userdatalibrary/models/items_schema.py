

ITEMS_JSON_SCHEMA_GENERIC = {
    "type": "object",
    "properties": {"type": {"type": "string"}},
    "required": ["type"],
}

ITEMS_JSON_SCHEMA_GEN3_GRAPHQL = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "type": {"type": "string"},
        "schema_version": {"type": "string"},
        "data": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "variables": {"oneOf": [{"type": "object"}]},
            },
            "required": ["query", "variables"],
        },
    },
    "required": ["name", "type", "schema_version", "data"],
}

ITEMS_JSON_SCHEMA_DRS = {
    "type": "object",
    "properties": {"dataset_guid": {"type": "string"}, "type": {"type": "string"}},
    "required": ["dataset_guid", "type"],
}

BLACKLIST = {"id", "creator", "created_time", "authz"}  # todo: would authz ever be updated?
