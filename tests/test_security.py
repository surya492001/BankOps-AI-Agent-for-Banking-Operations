"""The deployed API is protected by a shared key; local use stays open."""


def test_open_when_no_key_is_configured(client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    assert client.get("/incidents").status_code == 200


def test_rejects_requests_without_the_key(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret")
    assert client.get("/incidents").status_code == 401
    assert client.post("/demo/reset").status_code == 401
    assert client.get("/incidents", headers={"X-API-Key": "wrong"}).status_code == 401


def test_accepts_requests_with_the_key(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret")
    assert client.get("/incidents", headers={"X-API-Key": "s3cret"}).status_code == 200


def test_every_data_route_is_protected(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret")
    for path in ["/incidents/INC-1042", "/incidents/INC-1042/escalation", "/audit",
                 "/operations/summary", "/applications", "/sla/INC-1042"]:
        assert client.get(path).status_code == 401, path
    assert client.post("/agent/chat", json={"question": "hi"}).status_code == 401
    assert client.post("/incidents/INC-1042/escalate", json={"approved": True}).status_code == 401


def test_health_stays_open(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret")
    assert client.get("/health").json() == {"status": "ok"}
