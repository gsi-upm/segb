# Legacy API (0.4.x)

## What This Page Is For

SEGB 0.4.x had a different API, and the AMOR robots still call two of its routes. Version `1.2.0` keeps them so the
robots do not break while their configuration is moved to the native routes. They are **deprecated** and will be
removed by hand in 2.0, once nothing uses them.

## The Two Routes

| Legacy route | Native replacement | Notes |
|---|---|---|
| `POST /log` with a `text/turtle` body | `POST /ttl` with JSON `{"ttl_content": "<turtle>"}` | Same roles (`logger`, `admin`), same token rules, same storage and audit path. |
| `GET /health` | `GET /healthz/live` or `GET /healthz/ready` | `/healthz/ready` also reports whether Virtuoso is reachable. |

### `POST /log`

- Body: the Turtle itself, read as UTF-8 whatever the `Content-Type` is (0.4.x clients send `text/turtle`).
- `201` with `{"message": "Log saved successfully"}`; `422` for an empty body, a body that is not UTF-8 or invalid
  Turtle; `403` without the `logger` or `admin` role; `401` for a missing or invalid token.
- The upload is stored exactly as with `POST /ttl` and writes one audit entry whose route is `POST /log`.
  `POST /ttl` entries have the route `POST /ttl`.
- Send small logs for individual events; the same [insertion limits](api-and-roles.md#insert-turtle) apply.
- Unlike `POST /ttl`, it waits for a running transaction instead of answering `429`, so a burst of logs from several
  robots is queued rather than rejected.

### `GET /health`

Public, `200`, `text/plain`, with the running version (`SEGB is running. Version 1.3.1.`). The 0.4.x text was different;
clients that only check the status code are not affected. It is written to the server log only, never to the audit
trail.

### Tokens

Same as every native route: `username`, `roles` and `exp` are required. A token without `exp` is rejected with `401`.

## Deprecation Headers

Every response of the two routes, errors included, carries:

```text
Deprecation: true
Link: <https://semantic-ethical-glass-box.readthedocs.io/en/latest/reference/legacy-api/>; rel="deprecation"; type="text/html"
```

## Measuring Usage

`GET /legacy/usage` (role `admin`) counts the audit entries written through `POST /log`, with the first and last use:

```json
{
  "routes": {"POST /log": {"count": 128, "first_used_at": "2026-11-02T08:00:01.120934Z", "last_used_at": "2026-11-20T17:42:10.553120Z"}},
  "not_counted": ["GET /health (logged only, never audited)"]
}
```

The count is taken from the audit graph, so it survives restarts and needs no extra state. It is the evidence for
deciding when the legacy routes can go: removal is a manual decision, there is no automatic threshold.
