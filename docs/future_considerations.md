# Considerations

This file is for notes to be considered regarding the future of this repo

## Malicious links

Currently, it's possible for someone to store malicious links in our db (via the "items") property.
This is not an issue because they cannot share lists with other users. However, being able to share
lists is a future possible feature. In which case, we should address this issue, perhaps by utilizing a
third party allowlist/denylist source.

## Autogenerate openapi file

We should generate an actual openapi file instead of just the endpoint that
fast api currently generates for us. How do we do this?

## Abstraction Considerations

### Validation

Is there a better way to validate data coming into endpoints?
Currently, we use dependencies which work fine, but it duplicates code and queries.
Middleware is an option, but trying that required regex patterns.
We could bundle all queries into one dependency or just not have them and do
validation by endpoint, but that introduces the possibility of forgetting to test
an endpoint.

### Error handling

From what I have seen fastapi doesn't have any special way to handle
errors aside from raising http status codes. This is fine, but if we want
to abstract away error handling in the future, we may consider looking into
alternative design patters, particularly concepts such as the [`Result`](https://doc.rust-lang.org/std/result/) type.
Doing so would allow us to turn errors into data that can be pattern-matched
on, which will make the code a bit easier to organize.

## The sh file is blocking alembic from generating user lists table

Currently, if you run the sh files and the gen3 data library
postgres databases are not set up, the sh files will make
them. However, in doing so, if we then run alembic to
generate the tables, the user list table is not generated.

Ideally, we don’t want running the sh files to break the
alembic command, so we should look into this further and
figure out why alembic isn’t able to create the user list
table.

In the meantime, the workaround is to create the
databases manually, run alembic, and then you may run the
sh files
