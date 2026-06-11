from app.main import app


def test_openapi_schema_includes_analytics_route() -> None:
    schema = app.openapi()

    assert "/api/statistics/analytics" in schema["paths"]
    assert "/api/social/feed" in schema["paths"]
    assert "/api/social/people/{user_id}/follow" in schema["paths"]
    assert "/api/gamification" in schema["paths"]
