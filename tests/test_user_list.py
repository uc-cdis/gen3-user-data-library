from gen3userdatalibrary.models.user_list import is_dict, is_nonempty


def test_is_dict():
    """
    is_dict has an assert?

    TODO: Please someone refactor this at some point.
          We should just use isinstance() everywhere
          needed. This has a weird code smell
    """
    outcome = is_dict(dict())


def test_is_nonempty():
    """
    is_nonempty has an assert?

    TODO: Please someone refactor this at some point.
          We should just use isinstance() everywhere
          needed. This has a weird code smell
    """
    outcome = is_nonempty("aaa")


from gen3userdatalibrary.models.user_list import UserList
from gen3userdatalibrary.auth import get_lists_endpoint
from typing import Any, Dict
from datetime import datetime
import pytest


def create_mock_user_list(list_name: str = "My Test List") -> UserList:
    """Create  UserList object for simple testing"""

    # Define mock user list items content
    mock_user_list_items: Dict[str, Any] = {
        "drs://dg.4503:test-one": {
            "dataset_guid": "test.guid.01",
            "type": "GA4GH_DRS",
        },
        "drs://dg.4503:test-two": {
            "dataset_guid": "test.guid.02",
            "type": "GA4GH_DRS",
        },
        "CF_3": {
            "name": "Cohort Filter 3",
            "type": "Gen3GraphQL",
            "schema_version": "123456a",
            "data": {
                "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter){ file_count { histogram { sum } } } } }""",
                "variables": {
                    "filter": {
                        "AND": [
                            {"IN": {"annotated_sex": ["unknown"]}},
                            {"IN": {"data_type": ["Aligned Reads"]}},
                            {"IN": {"data_format": ["CRAM"]}},
                            {"IN": {"race": ['["unknown"]']}},
                        ]
                    }
                },
            },
        },
        "drs://dg.4503:test-four": {
            "dataset_guid": "test.guid.04",
            "type": "GA4GH_DRS",
        },
    }

    mock_user_list = UserList(
        version=0,
        creator=str("1"),
        # temporarily set authz without the list list_id since we haven't created the list in the db yet
        authz={"version": 0, "authz": [get_lists_endpoint("1")]},
        name=list_name,
        created_time=datetime.now(),
        updated_time=datetime.now(),
        items=mock_user_list_items,
    )
    return mock_user_list


def create_export_manifest(
    user_list: UserList, guid_list: list[str]
) -> list[str, Dict[str, Any]]:
    """Test compilation of export manifest from list.
    TBD: list obj is passed directly as param in this test, but this can be updated to list_id: str
    """

    # Initialize export manifest
    # Ex: [{"guid", "dataset_guid", "type"}]
    export_manifest = []

    # TBD? Get UserList based on unique identifier
    # Extract UserList items
    user_list_items = user_list.items

    # Format dict into list of tuples (ex. [(drsid, {dict details})}])
    items_formatted = list(user_list_items.items())
    for tuple_entry in items_formatted:
        tuple_dict = tuple_entry[1]
        tuple_dict_keys = list(tuple_dict.keys())
        # Skip if dataset guid not in dict details (means dataset is not a whole study pfb)
        if "dataset_guid" not in tuple_dict_keys:
            continue
        # If dataset guid in guid list, append to export_manifest
        if tuple_dict["dataset_guid"] in guid_list:
            tuple_dict["guid"] = tuple_entry[0].split("drs://")[-1]
            export_manifest.append(tuple_dict)

    return export_manifest


def test_create_export_manifest() -> Dict[str, Any] | None:
    """Creates export manifest."""

    # Test set-up: Ceate mock UserList for test
    mock_user_list = create_mock_user_list()
    # Placeholder: Get userlist model object from id (can update to get from test db)
    assert mock_user_list is not None
    assert "drs://dg.4503:test-one" in mock_user_list.items
    assert mock_user_list.name == "My Test List"

    # Create test export_manifest (with one guid)
    export_manifest = create_export_manifest(
        user_list=mock_user_list, guid_list=["test.guid.02"]
    )
    assert len(export_manifest) == 1
    assert "test.guid.02" in export_manifest[0].values()
    assert export_manifest[0]["guid"] == "dg.4503:test-two"

    # Create new test export_manifest (with two guids)
    test_guid_list = ["test.guid.02", "test.guid.04"]
    export_manifest = create_export_manifest(
        user_list=mock_user_list, guid_list=test_guid_list
    )
    assert len(export_manifest) == 2
    assert sorted([entry["dataset_guid"] for entry in export_manifest]) == sorted(
        test_guid_list
    )
    assert sorted([entry["guid"] for entry in export_manifest]) == sorted(
        ["dg.4503:test-two", "dg.4503:test-four"]
    )

    return
