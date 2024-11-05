# Questions

A doc for any non-specific questions about the api behavior.

## How do we ensure we don't, say, create a list for a non-existent user?

Endpoints can only be hit if a client has a valid token. To have a valid token, a user MUST exist.

## How can we be sure a user trying to update a list that does not belong to them fails?

As a part of our authorization process, we get the user's id. For all requests the user can make
the user can only access lists that are associated with that user id.
`
