from app.main import app


def test_openapi_schema_includes_analytics_route() -> None:
    schema = app.openapi()

    assert "/api/statistics/analytics" in schema["paths"]
    assert "/api/social/feed" in schema["paths"]
    assert "/api/social/people/{user_id}/follow" in schema["paths"]
    assert "/api/social/leaderboard" in schema["paths"]
    assert "/api/social/posts/{post_id}/comments" in schema["paths"]
    assert "/api/social/notifications" in schema["paths"]
    assert "/api/social/challenges" in schema["paths"]
    assert "/api/social/challenges/{challenge_id}/join" in schema["paths"]
    assert "/api/gamification" in schema["paths"]
