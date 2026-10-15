# PodcastHub

**A small, hands-on ActivityPub federation demonstration using podcasts.**

Two independent podcast servers can follow each other, publish episodes, and exchange ActivityStreams activities over HTTP. Designed for a WADe presentation, not public deployment.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Terminal 1:

```bash
PODCAST_HUB_PORT=8101 PODCAST_HUB_NAME="Aurora Podcasts" uvicorn podcasthub.app:app --host 127.0.0.1 --port 8101
```

Terminal 2:

```bash
PODCAST_HUB_PORT=8102 PODCAST_HUB_NAME="Orbit Podcasts" uvicorn podcasthub.app:app --host 127.0.0.1 --port 8102
```

Open <http://127.0.0.1:8101/> and <http://127.0.0.1:8102/> in your browser.

### 1. Follow a podcast on the other server

```bash
curl -X POST http://127.0.0.1:8102/follow -H 'Content-Type: application/json' \
  -d '{"actor":"http://127.0.0.1:8101/actors/podcast"}'
```

Orbit (8102) sends an ActivityPub `Follow` to Aurora (8101).

### 2. Publish an episode

```bash
curl -X POST http://127.0.0.1:8101/episodes -H 'Content-Type: application/json' \
  -d '{"title":"Episode 1","description":"Hello from Aurora!","url":"https://example.org/episode-1.mp3"}'
```

Aurora sends a `Create` activity containing a `Note` to its follower, Orbit.

### 3. Inspect federation

```bash
curl http://127.0.0.1:8101/events
curl http://127.0.0.1:8102/events
curl http://127.0.0.1:8102/actors/podcast/inbox
```

Use the browser's `/docs` on each server to make requests interactively.

## What this demonstrates

- Actor identity and discovery (`Person`, `inbox`, `outbox`)
- Following another independent server (`Follow`)
- Publishing a podcast announcement (`Create` + `Note`)
- Inbox delivery over real HTTP
- ActivityStreams JSON and a visible event log

## Important limitations

This is a **local-only subset**, not an interoperable public ActivityPub server. There are no HTTP signatures, authenticated federation, `Accept`/undo-follow workflows, delivery queues, retries or persistent accounts. The demo deliberately restricts destinations to localhost ports 8101 and 8102. Do not expose it to the public internet.

## Tests

```bash
python -m pytest -v
```

The unit tests check actor metadata and validation. See [docs/protocol.md](docs/protocol.md) for the sequence diagram and discussion.

For the complementary WebSub demonstration, see [podcast-relay](https://github.com/dragosandreibobu/podcast-relay).
