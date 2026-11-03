from drf_spectacular.generators import SchemaGenerator


def test_health_returns_ok_without_session(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_schema_exposes_status_property_and_example():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    media = schema["paths"]["/api/health"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]
    response_schema = media["schema"]
    if "$ref" in response_schema:
        name = response_schema["$ref"].rsplit("/", 1)[-1]
        response_schema = schema["components"]["schemas"][name]

    assert response_schema["type"] == "object"
    assert "status" in response_schema["properties"]
    assert {"status": "ok"} in [example["value"] for example in media["examples"].values()]
