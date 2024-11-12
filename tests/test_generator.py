import pytest

from tests.examples.examples import generate_numbers
from tests.examples.helpers_for_tests import async_iter


@pytest.mark.asyncio
async def test_generate_numbers(mocker):
    """
    An example of how to test a generating function
    the patch path must match where the function is used (not where it's defined) in your test file.

    Args:
        mocker: tool to mock functions
    """
    mocker.patch(
        "tests.examples.examples.number_generator",
        return_value=async_iter([4, 5, 6]),
    )
    outcome = await generate_numbers()
    assert outcome == [4, 5, 6]
