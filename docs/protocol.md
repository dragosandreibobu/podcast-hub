# ActivityPub podcast federation

## Demonstration flow

```text
Orbit (8102)                       Aurora (8101)
    |                                    |
    | GET /actors/podcast                |
    |----------------------------------->|
    |<----------- actor JSON ------------|
    |                                    |
    | POST Follow -> Aurora inbox        |
    |----------------------------------->|
    |<----------- 202 Accepted ----------|
    |                                    |
    |           Aurora publishes episode|
    |                                    |
    | GET Orbit actor document           |
    |<-----------------------------------|
    |------------ actor JSON ----------->|
    |                                    |
    | POST Create(Note) -> Orbit inbox   |
    |<-----------------------------------|
    |------------- 202 Accepted -------->|
```

The episode URL is ordinary HTTP content; the ActivityPub activity announces it rather than transporting the MP3 file.

### Actor

`GET /actors/podcast` returns an ActivityStreams actor with `id`, `inbox`, `outbox`, `followers`, and `following`.

### Follow

`POST /follow` constructs a `Follow` activity and delivers it to the other server's inbox. This teaching subset accepts the follow immediately; a complete ActivityPub implementation also models `Accept` and `Reject`.

### Create

`POST /episodes` constructs a `Create` activity containing a `Note` with the episode title, description and audio URL. The activity is delivered to the inbox of each local follower.

### Inspect

`GET /events` exposes received and sent activities, so the presenter can compare HTTP message direction and payloads.

## Protocol comparison

- **ActivityPub:** actors, social graph, following and federated activities.
- **WebSub:** topic subscriptions, hub verification and push delivery of changed resources.

The apps intentionally separate the two protocols so the presentation can explain their differences clearly.
