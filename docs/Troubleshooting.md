# Troubleshooting

This doc is to record common issues that crop up but are not issues that need to be fixed in the project

## I'm getting an arborist unavailable error?

Error:
`arborist unavailable; got requests exception: [Errno 8] nodename nor servname provided, or not known`

This is because `DEBUG_SKIP_AUTH` is set to `False`
