from fastapi.testclient import TestClient

from podcasthub.app import app, actor_document, local_actor


def test_actor_and_collections():
    client = TestClient(app)
    actor = client.get("/actors/podcast")
    assert actor.status_code == 200
    assert actor.headers["content-type"].startswith("application/activity+json")
    assert actor.json()["inbox"] == actor_document()["inbox"]
    assert client.get("/actors/podcast/outbox").json()["type"] == "OrderedCollection"


def test_local_actor_restriction():
    assert local_actor("http://127.0.0.1:8102/actors/podcast")
    assert not local_actor("https://example.org/actors/podcast")
    assert not local_actor("http://127.0.0.1:8102/admin")


def test_invalid_activity_rejected():
    client = TestClient(app)
    assert client.post("/actors/podcast/inbox", json={"type": "Delete"}).status_code == 400
    assert client.post("/episodes", json={"title": "Missing fields"}).status_code == 400
