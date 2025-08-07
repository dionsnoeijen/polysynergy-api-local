import inspect
from importlib import import_module
from pathlib import Path

_DISCOVERED_NODES = None
DEFAULT_PACKAGES = ["polysynergy_nodes"]

def discover_nodes(packages: list[str] = None):
    # global _DISCOVERED_NODES
    # if _DISCOVERED_NODES is not None:
    #     return _DISCOVERED_NODES

    packages = packages or DEFAULT_PACKAGES
    nodes = []

    for package in packages:
        try:
            mod = import_module(package)
            base_path = Path(mod.__file__).parent
        except Exception as e:
            print(f"Failed to import package {package}: {e}")
            continue

        for py_file in base_path.glob("*/[!_]*.py"):
            module_path = f"{package}.{py_file.parent.name}.{py_file.stem}"
            try:
                module = import_module(module_path)
            except Exception as e:
                print(f"Failed to import {module_path}: {e}")
                continue

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and getattr(obj, "_is_node", False):
                    try:
                        instance = obj()
                        nodes.append(instance.to_dict())
                    except Exception as e:
                        print(f"Failed to instantiate node {obj}: {e}")

    _DISCOVERED_NODES = nodes
    return nodes