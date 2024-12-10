from gen3userdatalibrary.models.user_list import is_dict, is_nonempty


def test_is_dict():
    outcome = is_dict(dict())


def test_is_nonempty():
    outcome = is_nonempty("aaa")
