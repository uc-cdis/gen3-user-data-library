import time

from starlette.responses import JSONResponse
from fastapi import HTTPException
from jsonschema.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.models.user_list import UserList, ItemToUpdateModel
from gen3userdatalibrary.services.helpers.modeling import create_user_list_instance


async def try_conforming_list(user_id, user_list: ItemToUpdateModel) -> UserList:
    """
    Handler for modeling endpoint data into a user list orm
    user_id: list creator's id
    user_list: dict representation of the user's list
    """
    try:
        list_as_orm = await create_user_list_instance(user_id, user_list)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="must provide a unique name")
    except ValidationError:
        config.logging.debug(f"Invalid user-provided data when trying to create lists for user {user_id}.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    except Exception as exc:
        config.logging.exception(f"Unknown exception {type(exc)} when trying to create lists for user {user_id}.")
        config.logging.debug(f"Details: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    return list_as_orm


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
