def test_health_response_has_security_headers(client):
    response = client.get("/api/health")

    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "no-referrer"
    assert response["Cache-Control"] == "no-store"
