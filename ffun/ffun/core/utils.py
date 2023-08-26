import datetime
import importlib
import pathlib
import sys
import types


def now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def discover_submodules(parent_module: str) -> list[types.ModuleType]:
    parent = sys.modules.get(parent_module)

    if parent is None:
        parent = importlib.import_module(parent_module)

    if not hasattr(parent, "__path__"):
        return []

    parent_dir = pathlib.Path(parent.__path__[0])

    candidates = []

    for module_path in parent_dir.glob("*.py"):
        module_name = module_path.stem
        candidates.append(f"{parent_module}.{module_name}")

    for module_path in parent_dir.glob("*/__init__.py"):
        module_name = module_path.parent.stem
        candidates.append(f"{parent_module}.{module_name}")

    child_modules = []

    for full_module_name in candidates:
        submodule = sys.modules.get(full_module_name)

        if submodule is None:
            submodule = importlib.import_module(full_module_name)

        child_modules.append(submodule)

    return child_modules
