from app.main import app


def test_openapi_schema_includes_analytics_route() -> None:
    schema = app.openapi()

    assert "/api/statistics/analytics" in schema["paths"]
