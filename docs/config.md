# Config

This doc will offer an explanation for the various properties that are 
configurable in this repo's env

# ENV

This variable is used to look for the .env file. Useful if you have different .env configurations for, say,
prod or testing

## DB_CONNECTION_STRING

This property defines the postgres configuration string to connect to the database. 
Make sure you have `postgresql+asyncpg` or you'll get errors about the default psycopg 
not supporting async.

## DEBUG

Changes the logging from INFO to DEBUG

## DEBUG_SKIP_AUTH

If set to true, the service will completely skip all authorization; typically for debugging 
purposes. 

## MAX_LISTS

Defines the maximum number of lists a user can have. 

NOTE: If a user has N number of lists and the configuration is set to N - M, the user
will maintain N number of lists, but they will be unable to add more.

## MAX_LIST_ITEMS

Defines the maximum number of items a user can have for a given list. 

NOTE: If a user has N number of items and the configuration is set to N - M, the user
will maintain N number of items, but they will be unable to add more.

## SCHEMAS_LOCATION

This property defines where the validation schema mapping definition is
located. It should be a json file. More details abut the validation
schema in the next section. 

## ITEM_SCHEMAS

Holds a dictionary of schema `type` => schema properties. When a request comes
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
      "type": "GA4GH_DRS"}}}
```