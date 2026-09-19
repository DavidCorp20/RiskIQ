from app.main import app


def test_dsi_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/reports/dsi-export" in paths
    assert "/api/v1/reports/verify/{digest}" in paths
