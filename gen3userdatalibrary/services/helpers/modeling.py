import datetime

from gen3userdatalibrary.models.user_list import ItemToUpdateModel, UserList
from gen3userdatalibrary.services.auth import get_lists_endpoint


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
