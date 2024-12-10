async def number_generator():
    yield 1
    yield 2
    yield 3


async def async_iter(values):
    """
    Helper function to return an async iterator
    """
    for value in values:
        yield value
