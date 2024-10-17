import datetime

from fastapi import HTTPException
from jsonschema.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.models.user_list import ItemToUpdateModel, UserList
from gen3userdatalibrary.services.auth import get_lists_endpoint


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


async def create_user_list_instance(user_id, user_list: ItemToUpdateModel):
    """
    Creates a user list orm given the user's id and a dictionary representation.
    Tests the type
    Assumes user list is in the correct structure

    """
    assert user_id is not None, "User must have an ID!"
    now = datetime.datetime.now(datetime.timezone.utc)
    name = user_list.name or f"Saved List {now}"
    user_list_items = user_list.items or {}

    new_list = UserList(version=0, creator=str(user_id),
                        # temporarily set authz without the list ID since we haven't created the list in the db yet
                        authz={"version": 0, "authz": [get_lists_endpoint(user_id)]}, name=name, created_time=now,
                        updated_time=now, items=user_list_items)
    return new_list
