# Schemas

This file is meant to act as a source of info on schema definitions 
for the item component of user lists.

## General Structure

```json
{
  "<schema_name>": {
    "type": "object",
    "properties": { "x": "..." },
    "required": ["x", "..."]
  }
}
```

### Object Structure

```json
{
  "type": "object",
  "properties": { "prop1": "...", "prop2": "...", "prop3":  "..."},
  "required": [ "prop1", "prop3"]
}
```

### String

```json
{
  "<name>": {
    "type": "string"
  }
}
```