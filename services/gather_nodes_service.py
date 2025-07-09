import inspect
from importlib import import_module
from pathlib import Path
import polysynergy_nodes

_DISCOVERED_NODES = None

def discover_nodes():
    global _DISCOVERED_NODES
    if _DISCOVERED_NODES is not None:
        return _DISCOVERED_NODES

    base_path = Path(polysynergy_nodes.__file__).parent
    base_import = "polysynergy_nodes"
    nodes = []

    for py_file in base_path.glob("*/[!_]*.py"):  # alle *.py bestanden direct onder 'nodes/'
        module_path = f"{base_import}.{py_file.parent.name}.{py_file.stem}"
        try:
            module = import_module(module_path)
        except Exception as e:
            print(f"❌ Failed to import {module_path}: {e}")
            continue

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and getattr(obj, "_is_node", False):
                try:
                    instance = obj()
                    nodes.append(instance.to_dict())  # 👈 hier
                except Exception as e:
                    print(f"⚠️ Failed to instantiate node {obj}: {e}")

    _DISCOVERED_NODES = nodes
    return nodes