from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app


def _registered_paths() -> set[str]:
    paths: set[str] = set()

    def collect(routes) -> None:
        for route in routes:
            if isinstance(route, APIRoute):
                paths.add(route.path)
            nested = getattr(route, "routes", None)
            if nested:
                collect(nested)

    collect(app.routes)
    return paths


def test_dsi_routes_registered():
    paths = _registered_paths()
    assert "/api/v1/reports/dsi-export" in paths
    assert "/api/v1/reports/verify/{digest}" in paths
