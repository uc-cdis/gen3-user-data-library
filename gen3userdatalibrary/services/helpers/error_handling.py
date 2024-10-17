import time

from starlette import status
from starlette.responses import JSONResponse


def build_generic_500_response():
    return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    status_text = "UNHEALTHY"
    response = {"status": status_text, "timestamp": time.time()}
    return JSONResponse(status_code=return_status, content=response)


async def make_db_request_or_return_500(primed_db_query, fail_handler=build_generic_500_response):
    try:
        outcome = await primed_db_query()
        return True, outcome
    except Exception as e:
        outcome = fail_handler()
        return False, outcome
