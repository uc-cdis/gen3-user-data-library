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
