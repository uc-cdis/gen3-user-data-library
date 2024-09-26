import datetime
from functools import reduce
from jsonschema import ValidationError, validate
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect


async def try_conforming_list(user_id, user_list: dict) -> UserList:
    """
    Handler for modeling endpoint data into orm

    :param user_list: dictionary representation of user list object
    :param user_id: id of the list owner
    :return: user list orm
    """
    try:
        list_as_orm = await create_user_list_instance(user_id, user_list)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="must provide a unique name")
    except ValidationError as exc:
        logging.debug(f"Invalid user-provided data when trying to create lists for user {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided")
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to create lists for user {user_id}.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided")
    return list_as_orm


def validate_user_list_item(item_contents):
    """
    Ensures that the item component of a user list has the correct setup for type property

    """
    # TODO THIS NEEDS TO BE CFG
    if item_contents.get("type") == "GA4GH_DRS":
        try:
            validate(instance=item_contents, schema=ITEMS_JSON_SCHEMA_DRS)
        except ValidationError as e:
            logging.debug(f"User-provided JSON is invalid: {e.message}")
            raise
    elif item_contents.get("type") == "Gen3GraphQL":
        try:
            validate(instance=item_contents, schema=ITEMS_JSON_SCHEMA_GEN3_GRAPHQL, )
        except ValidationError as e:
            logging.debug(f"User-provided JSON is invalid: {e.message}")
            raise
    else:
        try:
            validate(instance=item_contents, schema=ITEMS_JSON_SCHEMA_GENERIC)
        except ValidationError as e:
            logging.debug(f"User-provided JSON is invalid: {e.message}")
            raise

        logging.warning("User-provided JSON is an unknown type. Creating anyway...")


async def create_user_list_instance(user_id, user_list: dict):
    """
    Creates a user list orm given the user's id and a dictionary representation.
    Tests the type
    Assumes user list is in the correct structure
    """
    # next todo: is there a way to move this out reasonably?
    assert user_id is not None, "User must have an ID!"
    now = datetime.datetime.now(datetime.timezone.utc)
    name = user_list.get("name", f"Saved List {now}")
    user_list_items = user_list.get("items", {})

    all(validate_user_list_item(item) for item in user_list_items.values())

    new_list = UserList(
        version=0,
        creator=str(user_id),
        # temporarily set authz without the list ID since we haven't created the list in the db yet
        authz={
            "version": 0,
            "authz": [get_lists_endpoint(user_id)],
        },
        name=name,
        created_time=now,
        updated_time=now,
        items=user_list_items)
    return new_list


def find_differences(list_to_update, new_list):
    """
    Finds differences in attributes between two SQLAlchemy ORM objects of the same type.
    """
    mapper = inspect(list_to_update).mapper

    def add_difference(differences, attribute):
        attr_name = attribute.key
        value1 = getattr(list_to_update, attr_name)
        value2 = getattr(new_list, attr_name)
        if value1 != value2:
            differences[attr_name] = (value1, value2)
        return differences

    differences_between_lists = reduce(add_difference, mapper.attrs, {})
    return differences_between_lists
