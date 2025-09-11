from importlib import import_module
from typing import Any, Callable

from core.bootstrap_engine import BootstrapEngine


def get_function_from_string(spec: str) -> Callable[..., Any]:
    """Resolve ``module[:function]`` strings to callables."""
    if ":" in spec:
        module_path, func_name = spec.split(":", 1)
        module = import_module(module_path)
        return getattr(module, func_name)
    try:
        module = import_module(spec)
    except ModuleNotFoundError:
        module_path, func_name = spec.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, func_name)
    for name in ("on_init", "on_message", "main", "initialize", "handler"):
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(f"No callable found for {spec}")


def main() -> None:
    engine = BootstrapEngine()
    agent = engine.load_agent("enrichment_agent_v1")
    on_init = get_function_from_string(agent["entry_points"]["on_init"])
    on_message = get_function_from_string(agent["entry_points"]["on_message"])
    engine.run(on_init, on_message)


if __name__ == "__main__":
    main()
