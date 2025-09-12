"""Utilities for dynamic imports."""

from importlib import import_module
from typing import Callable


def get_function_from_string(path: str) -> Callable:
    """Return a function object from a dotted path string.

    Parameters
    ----------
    path:
        Dotted path in the form ``"package.module.function"``.

    Raises
    ------
    ImportError
        If the module cannot be imported.
    AttributeError
        If the function does not exist in the module.
    """

    module_path, func_name = path.rsplit(".", 1)
    module = import_module(module_path)
    func = getattr(module, func_name)
    if not callable(func):  # pragma: no cover - safety check
        raise TypeError(f"{path} is not callable")
    return func
