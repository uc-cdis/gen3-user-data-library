## ITEM_SCHEMAS

Follows the [json schema](https://json-schema.org/learn/json-schema-examples) convention. When a request comes
to the api that creates or updates the `items` component, it must first
conform to a valid schema. This schema formation is defined in a
`items_schemas.json` file that is loaded in at runtime. Each `items` element (say I)
should have a corresponding `type` component (say C) that conforms to the key in
the `items_schema.json` file. In doing so, the api will validate that I conforms
to the schema defined at the type matching C. If you provide a schema with
the name `"None"` (matching Python's null use case), that schema will be used
as the default for any schemas who do not have a matching type.
Example:

`items_schema.json`

```json
{
  "GA4GH_DRS": {
    "type": "object",
    "properties": {
      "dataset_guid": {
        "type": "string"
      },
      "type": {
        "type": "string"
      }
    },
    "required": [
      "dataset_guid",
      "type"
    ]
  },
  "None": {
    "type": "object",
    "properties": {
      "type": {
        "type": "string"
      }
    },
    "required": [
      "type"
    ]
  }
}
```

Example request:

```json
    {
  "items": {
    "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
      "dataset_guid": "phs000001.v1.p1.c1",
      "type": "GA4GH_DRS"
    }
  }
}
```