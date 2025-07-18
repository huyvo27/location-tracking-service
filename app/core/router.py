import importlib
import pkgutil
from pathlib import Path

from fastapi import APIRouter

API_PATH = Path(__file__).parent.parent / "api"
API_PATH_V1 = API_PATH / "v1"
WEBSOCKET_PATH = Path(__file__).parent.parent / "websocket/endpoints"


def auto_include_routers(package: str, path: Path) -> APIRouter:
    """
    Dynamically imports and includes FastAPI routers from a specified package and path.

    This function scans the given directory for Python modules, imports them, and checks
    if they contain a `router` attribute. If a `router` is found, it is included in the
    main router with a prefix based on the module name and a tag for the module.

    Args:
        package (str): The Python package name where the modules are located.
        path (Path): The file system path to the directory containing the modules.

    Returns:
        APIRouter: A FastAPI APIRouter instance with all discovered routers included.
    """
    router = APIRouter()
    for _, module_name, is_pkg in pkgutil.iter_modules([str(path)]):
        if not is_pkg:
            module_path = f"{package}.{module_name}"
            module = importlib.import_module(module_path)
            if hasattr(module, "router"):
                router.include_router(
                    getattr(module, "router"),
                    prefix="/" + module_name,
                    tags=[module_name],
                )
    return router


base_router = auto_include_routers(package="app.api", path=API_PATH)
v1_router = auto_include_routers(package="app.api.v1", path=API_PATH_V1)
ws_router = auto_include_routers(package="app.websocket.endpoints", path=WEBSOCKET_PATH)
