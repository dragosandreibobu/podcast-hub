"""Real HTTP federation smoke test: two independent Uvicorn processes."""
import contextlib
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest


def _free(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


@pytest.fixture
def servers():
    if not all(_free(port) for port in (8101, 8102)):
        pytest.skip("Demo ports 8101/8102 are occupied")
    processes = []
    try:
        for port, name in ((8101, "Aurora"), (8102, "Orbit")):
            env = dict(os.environ, PODCAST_HUB_PORT=str(port), PODCAST_HUB_NAME=name)
            processes.append(subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "podcasthub.app:app",
                 "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            ))
        with httpx.Client(timeout=.4, trust_env=False) as client:
            for _ in range(80):
                for proc in processes:
                    if proc.poll() is not None:
                        pytest.fail("ActivityPub service exited before becoming ready")
                try:
                    if all(client.get(f"http://127.0.0.1:{port}/actors/podcast").status_code == 200
                           for port in (8101, 8102)):
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            else:
                pytest.fail("ActivityPub services did not become ready")
        yield
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()


def test_follow_and_publish_over_http(servers):
    with httpx.Client(timeout=5, trust_env=False) as client:
        aurora = "http://127.0.0.1:8101"
        orbit = "http://127.0.0.1:8102"
        followed = client.post(f"{orbit}/follow", json={"actor": f"{aurora}/actors/podcast"})
        assert followed.status_code == 201, followed.text
        assert followed.json()["type"] == "Follow"
        assert f"{orbit}/actors/podcast" in client.get(f"{aurora}/actors/podcast/followers").json()["items"]

        published = client.post(f"{aurora}/episodes", json={
            "title": "Federated Episode", "description": "Cross-server test",
            "url": "https://example.org/episode.mp3",
        })
        assert published.status_code == 201, published.text
        assert published.json()["delivered"] == 1
        inbox = client.get(f"{orbit}/actors/podcast/inbox").json()
        assert inbox["totalItems"] == 1
        activity = inbox["orderedItems"][0]
        assert activity["type"] == "Create"
        assert activity["object"]["name"] == "Federated Episode"
        assert activity["actor"] == f"{aurora}/actors/podcast"
        assert any(event["direction"] == "inbound" for event in client.get(f"{orbit}/events").json())
