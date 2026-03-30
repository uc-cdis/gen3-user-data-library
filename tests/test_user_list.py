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
