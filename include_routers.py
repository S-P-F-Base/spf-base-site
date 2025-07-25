import importlib
import importlib.util
import pkgutil

from fastapi import APIRouter


def include_routers_from_package(package_name: str) -> APIRouter:
    router = APIRouter()

    spec = importlib.util.find_spec(package_name)
    if spec is None or spec.submodule_search_locations is None:
        raise ImportError(f"Cannot find package {package_name}")

    package_path = list(spec.submodule_search_locations)

    for _, module_name, is_pkg in pkgutil.iter_modules(package_path):
        if is_pkg:
            continue

        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        if hasattr(module, "router"):
            router.include_router(getattr(module, "router"))

    return router
