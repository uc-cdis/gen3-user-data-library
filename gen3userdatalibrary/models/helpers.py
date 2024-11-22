import datetime

from fastapi import HTTPException
from jsonschema.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.auth import get_lists_endpoint
from gen3userdatalibrary.models.user_list import ItemToUpdateModel, UserList


async def try_conforming_list(user_id, user_list: ItemToUpdateModel) -> UserList:
    """
    Handler for modeling endpoint data into a user list orm
    user_id: list creator's id
    user_list: dict representation of the user's list
    """
    try:
        list_as_orm = await create_user_list_instance(user_id, user_list)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "info": f"Invalid user id: {user_id}",
                "error": exc.__class__.__name__,
            },
        )
    except Exception as exc:
        config.logging.exception(
            f"Unknown exception {type(exc)} when trying to create lists for user {user_id}."
        )
        config.logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "info": "Invalid list information provided",
                "error": exc.__class__.__name__,
            },
        )
    return list_as_orm


async def create_user_list_instance(user_id, user_list: ItemToUpdateModel):
    """
    Creates a user list orm given the user's id and a dictionary representation.
    Tests the type
    Assumes user list is in the correct structure

    """
    if user_id is None:
        raise ValueError("User must have an id!")
    now = datetime.datetime.now(datetime.timezone.utc)
    name = user_list.name or f"Saved List {now}"
    user_list_items = user_list.items or {}

    new_list = UserList(
        version=0,
        creator=str(user_id),
        # temporarily set authz without the list list_id since we haven't created the list in the db yet
        authz={"version": 0, "authz": [get_lists_endpoint(user_id)]},
        name=name,
        created_time=now,
        updated_time=now,
        items=user_list_items,
    )
    return new_list
