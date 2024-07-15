from typing import Any


class Factory:
    """
    Simple object-oriented factory to register classes and
    get instances based on a string name input.
    """

    def __init__(self) -> None:
        """
        Sets up the internal dict for storing the mappings
        """
        self._classes = {}

    def register(self, class_name: str, class_def: object) -> None:
        """
        Add a class to the registry under the provided name.

        Args:
            class_name (str): Provided name for the class
            class_def (object): Actual class definition object
        """
        self._classes[class_name] = class_def

    def get(self, class_name: str, *args, **kwargs) -> Any:
        """
        Get an instance of the class specified by the name (it must have
        been previously registered).

        This passes along the provided args/kwargs into the initialization of
        the class.

        Args:
            class_name (str): Provided name for the class
            *args: any args to pass to the class initialization
            **kwargs: any keyword args to pass to the class initialization

        Returns:
            object: Instance of registered class definition for the name specified

        Raises:
            ValueError: No registered class exists with provided name
        """
        class_def = self._classes.get(class_name)
        if not class_def:
            raise ValueError(class_name)
        return class_def(*args, **kwargs)
