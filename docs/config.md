# Config

This doc will offer an explanation for the various properties that are 
configurable in this repo's env

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

## ITEM_SCHEMAS

Holds a dictionary of schema type => schema properties. When list requests come 
into this api, our validation will ensure that the "items" component of an 
update request conforms to the schema defined in a `items_schemas.json` file that
should be in a `config` directory at the top level. The specific schema
to conform to is defined by the item's type. If you provide a schema with 
the name `"None"` (matching Python's null use case), that schema will be used
as the default for any schemas who do not have a matching type.
Example: 
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