"""Minimal local ActivityPub podcast federation demo.

This is an inspectable ActivityPub subset, not a public interoperable server.
Run on 127.0.0.1 only; inbox delivery is deliberately restricted to loopback.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from podcasthub.ui import demo_page

CONTEXT = "https://www.w3.org/ns/activitystreams"
HOST = os.getenv("PODCAST_HUB_HOST", "127.0.0.1")
PORT = int(os.getenv("PODCAST_HUB_PORT", "8101"))
NAME = os.getenv("PODCAST_HUB_NAME", "Aurora Podcasts")
BASE = f"http://{HOST}:{PORT}"
ACTOR = f"{BASE}/actors/podcast"
app = FastAPI(title=f"PodcastHub - {NAME}")
FOLLOWERS: set[str] = set()
FOLLOWING: set[str] = set()
OUTBOX: list[dict] = []
INBOX: list[dict] = []
EVENTS: list[dict] = []


def local_actor(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (
            p.scheme == "http" and p.hostname in {"127.0.0.1", "localhost"}
            and p.port in {8101, 8102} and p.path == "/actors/podcast"
            and not p.username and not p.password and not p.query and not p.fragment
        )
    except ValueError:
        return False


def actor_document():
    return {
        "@context": CONTEXT, "id": ACTOR, "type": "Person",
        "preferredUsername": "podcast", "name": NAME,
        "inbox": f"{ACTOR}/inbox", "outbox": f"{ACTOR}/outbox",
        "followers": f"{ACTOR}/followers", "following": f"{ACTOR}/following",
    }


def log(direction: str, target: str, activity: dict, status: int | None = None):
    EVENTS.append({"direction": direction, "target": target, "type": activity.get("type"),
                   "activity": activity, "status": status})


async def send(target_actor: str, activity: dict):
    if not local_actor(target_actor):
        raise HTTPException(400, "Only the two local demo actors are allowed")
    # Resolve the remote actor document rather than assuming its inbox.
    async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
        try:
            response = await client.get(target_actor, headers={"Accept": "application/activity+json"})
            response.raise_for_status()
            remote = response.json()
            inbox = remote.get("inbox")
            if inbox != target_actor + "/inbox":
                raise HTTPException(400, "Unexpected remote inbox")
            delivery = await client.post(inbox, json=activity,
                                         headers={"Content-Type": "application/activity+json"})
            delivery.raise_for_status()
        except httpx.HTTPError as exc:
            log("outbound-failed", target_actor, activity)
            raise HTTPException(502, "Remote actor unavailable") from exc
    log("outbound", inbox, activity, delivery.status_code)


@app.get("/", response_class=HTMLResponse)
def home():
    posts = "".join(f"<li><strong>{escape(str(a['object'].get('name', 'Episode')))}</strong>: "
                    f"{escape(str(a['object'].get('content', '')))}</li>"
                    for a in OUTBOX if a.get("type") == "Create")
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>{escape(NAME)} - PodcastHub</title>
<style>body{{font:16px system-ui;max-width:780px;margin:3rem auto;padding:1rem;background:#f8fafc;color:#0f172a}}
a{{color:#075985}}code,pre{{background:#e2e8f0;padding:.4rem;border-radius:5px}}
li{{margin:.6rem 0}}</style>
<h1>{escape(NAME)}</h1><p>Independent ActivityPub podcast server: <code>{escape(ACTOR)}</code></p>
<p><a href="/demo">Interactive demo</a> · <a href="/docs">API</a> · <a href="/events">Protocol events (JSON)</a> ·
<a href="/actors/podcast/outbox">Outbox</a> · <a href="/actors/podcast/inbox">Inbox</a></p>
<h2>Published episodes</h2><ul>{posts or '<li>No episodes yet</li>'}</ul>
<p>Followers: {len(FOLLOWERS)} · Following: {len(FOLLOWING)} · Received activities: {len(INBOX)}</p>
</html>"""


@app.get("/demo", response_class=HTMLResponse)
def demo():
    return demo_page(NAME, BASE)


@app.get("/actors/podcast")
def actor():
    from fastapi.responses import JSONResponse
    return JSONResponse(actor_document(), media_type="application/activity+json")


@app.get("/actors/podcast/outbox")
def outbox():
    return {"@context": CONTEXT, "id": f"{ACTOR}/outbox", "type": "OrderedCollection",
            "totalItems": len(OUTBOX), "orderedItems": list(reversed(OUTBOX))}


@app.get("/actors/podcast/inbox")
def inbox():
    return {"@context": CONTEXT, "id": f"{ACTOR}/inbox", "type": "OrderedCollection",
            "totalItems": len(INBOX), "orderedItems": list(reversed(INBOX))}


@app.get("/actors/podcast/followers")
def followers():
    return {"@context": CONTEXT, "type": "Collection", "totalItems": len(FOLLOWERS),
            "items": sorted(FOLLOWERS)}


@app.get("/actors/podcast/following")
def following():
    return {"@context": CONTEXT, "type": "Collection", "totalItems": len(FOLLOWING),
            "items": sorted(FOLLOWING)}


@app.get("/events")
def events():
    return EVENTS


@app.post("/follow", status_code=201)
async def follow(body: dict):
    target = body.get("actor")
    if not isinstance(target, str) or not local_actor(target) or target == ACTOR:
        raise HTTPException(400, "Specify the other local podcast actor")
    activity = {"@context": CONTEXT, "id": f"{BASE}/activities/{uuid4()}",
                "type": "Follow", "actor": ACTOR, "object": target}
    await send(target, activity)
    FOLLOWING.add(target)
    OUTBOX.append(activity)
    return activity


@app.post("/episodes", status_code=201)
async def episode(body: dict):
    title, content, url = body.get("title"), body.get("description"), body.get("url")
    if not all(isinstance(v, str) and v.strip() for v in (title, content, url)):
        raise HTTPException(400, "title, description and url are required strings")
    if urlsplit(url).scheme not in {"http", "https"}:
        raise HTTPException(400, "Episode URL must be HTTP(S)")
    note_id = f"{BASE}/episodes/{uuid4()}"
    activity = {
        "@context": CONTEXT, "id": f"{BASE}/activities/{uuid4()}",
        "type": "Create", "actor": ACTOR,
        "to": [f"{ACTOR}/followers"],
        "object": {"id": note_id, "type": "Note", "attributedTo": ACTOR,
                   "name": title, "content": content, "url": url,
                   "published": datetime.now(timezone.utc).isoformat(),
                   "to": [f"{ACTOR}/followers"]},
    }
    OUTBOX.append(activity)
    delivered = 0
    for follower in sorted(FOLLOWERS):
        try:
            await send(follower, activity)
            delivered += 1
        except HTTPException:
            pass
    return {"activity": activity, "delivered": delivered}


@app.post("/actors/podcast/inbox", status_code=202)
async def receive(request: Request):
    if len(await request.body()) > 100_000:
        raise HTTPException(413, "Activity too large")
    try:
        activity = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "Invalid JSON") from exc
    if not isinstance(activity, dict) or activity.get("type") not in {"Follow", "Create"}:
        raise HTTPException(400, "Only Follow and Create are demonstrated")
    origin = activity.get("actor")
    if not isinstance(origin, str) or not local_actor(origin) or origin == ACTOR:
        raise HTTPException(400, "Invalid local actor")
    if activity["type"] == "Follow":
        if activity.get("object") != ACTOR:
            raise HTTPException(400, "Follow must target this actor")
        FOLLOWERS.add(origin)
    else:
        obj = activity.get("object")
        if not isinstance(obj, dict) or obj.get("type") != "Note" or obj.get("attributedTo") != origin:
            raise HTTPException(400, "Create must contain an attributed Note")
    INBOX.append(activity)
    log("inbound", f"{ACTOR}/inbox", activity, 202)
    return {"accepted": True}
