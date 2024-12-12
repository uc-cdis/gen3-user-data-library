import importlib
import inspect
from pathlib import Path, PosixPath
from types import ModuleType
from typing import Dict


def get_modules_in_directory(directory: Path) -> Dict[str, ModuleType]:
    """
    Creates a module name => module instance mapping
    Args:
        directory (PosixPath): directory with source file modules

    Returns:
        module name => module instance mapping
    """
    filenames = [
        file.relative_to(directory.parent)
        for file in directory.rglob("*.py")
        if file.is_file()
    ]
    python_files = list(
        filter(
            lambda filename: filename.suffix == ".py"
            and not filename.name == "__init__.py",
            filenames,
        )
    )
    module_names = list(
        map(
            lambda py_file: py_file.with_suffix("").as_posix().replace("/", "."),
            python_files,
        )
    )
    module_name_to_instance = dict(
        map(
            lambda module_name: (module_name, importlib.import_module(module_name)),
            module_names,
        )
    )
    return module_name_to_instance


def get_functions_from_module(module_name: str, service_module: ModuleType):
    """
    Create function name => function mapping, N, for importlib

    Args:
        module_name (str): full module name
        service_module (ModuleType): name for module to import functions for

    Returns:
        (module_name, N)
    """
    functions_in_module = inspect.getmembers(service_module, inspect.isfunction)
    function_name_to_instance = {name: obj for name, obj in functions_in_module}
    return module_name, function_name_to_instance


SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "gen3userdatalibrary"
PROJECT_MODULES = get_modules_in_directory(SOURCE_DIRECTORY)
MODULES_TO_FUNCTIONS = dict(
    map(lambda pm: get_functions_from_module(*pm), PROJECT_MODULES.items())
)
