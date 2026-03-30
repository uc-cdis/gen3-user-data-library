from tests.examples.helpers_for_tests import number_generator


async def generate_numbers():
    """
    return a list of generated numbers
    """
    r = [value async for value in number_generator()]
    return r
