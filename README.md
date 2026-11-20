# EventFlow

EventFlow is a webhook delivery platform built with Django REST Framework.

Your application sends an event to EventFlow. The platform stores it, creates a
delivery for every matching webhook endpoint, sends signed HTTP requests,
retries on failures and keeps the full history of every attempt.

## Features

- Webhook endpoint management (create, update, activate, deactivate)
- Event ingestion with idempotency keys
- Asynchronous delivery with Celery
- Automatic retries with exponential backoff
- HMAC-SHA256 request signatures
- Full delivery and attempt history
- Manual retry of failed deliveries
- Transactional Outbox: events are not lost if the broker is down
- Recovery of deliveries stuck after a worker crash
- SSRF protection for endpoint URLs
- Rate limiting and payload size limits
- OpenAPI / Swagger documentation

## Tech Stack

- Python, Django, Django REST Framework
- PostgreSQL
- Redis
- Celery and Celery Beat
- HTTPX
- drf-spectacular
- Docker (in progress)

## How it works

1. Register an endpoint, for example `https://example.com/webhooks`.
2. Subscribe it to event types such as `order.created`.
3. Send an event with `POST /api/events/`.
4. EventFlow creates a delivery for each active endpoint subscribed to that type.
5. Celery sends the HTTP POST requests and retries temporary failures.
6. Inspect results with `GET /api/deliveries/` and retry failed ones.

Delivery guarantee: **at-least-once**. The same event may be delivered more
than once, so receivers must deduplicate (see below).

## Getting started

### Requirements

- Python 3.11+
- PostgreSQL
- Redis

### Setup

```bash
git clone <your-repo-url>
cd eventflow
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=eventflow
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Run migrations and start the three processes (in separate terminals):

```bash
python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
celery -A config worker -l info
celery -A config beat -l info
```

Celery Beat is required: it runs the outbox dispatcher, scheduled retries
and recovery of stuck deliveries.

## API overview

Interactive documentation is available in Swagger (usually `/api/docs/`).
All endpoints require authentication, and users only see their own data.

| Method | URL | Description |
|---|---|---|
| POST | `/api/endpoints/` | Create endpoint (the secret is shown only here) |
| GET | `/api/endpoints/` | List your endpoints |
| PATCH | `/api/endpoints/{id}/` | Update name, url, subscribed events |
| POST | `/api/endpoints/{id}/activate/` | Enable delivery |
| POST | `/api/endpoints/{id}/deactivate/` | Disable delivery |
| POST | `/api/endpoints/{id}/rotate-secret/` | Issue a new secret (shown once) |
| POST | `/api/events/` | Send an event |
| GET | `/api/events/` | List events (filters: `event_type`, `created_after`, `created_before`) |
| GET | `/api/events/{id}/` | Event with its deliveries |
| GET | `/api/deliveries/` | List deliveries (filters: `status`, `event`, `endpoint`, dates) |
| GET | `/api/deliveries/{id}/` | Delivery with attempt history |
| POST | `/api/deliveries/{id}/retry/` | Retry a failed delivery |
| GET | `/api/delivery-attempts/?delivery_id={id}` | Attempts of a delivery |

### Sending an event

```http
POST /api/events/
Content-Type: application/json

{
  "event_type": "order.created",
  "idempotency_key": "order-1001-created",
  "payload": {"order_id": 1001, "total": 49.90}
}
```

- `idempotency_key` must be unique per account. Repeating it returns `409`.
- Maximum payload size: 64 KB.
- Rate limit for event creation: 60 requests per minute.

### Delivery statuses

| Status | Meaning |
|---|---|
| `pending` | Waiting to be sent |
| `processing` | A worker is sending it now |
| `success` | Receiver answered with 2xx |
| `failed` | Failed. Retried automatically if the error is temporary |

## Receiving webhooks

### What you receive

`POST` with `Content-Type: application/json`:

```json
{
  "id": "6f1c0c1e-0000-0000-0000-000000000000",
  "event_type": "order.created",
  "payload": {"order_id": 1001},
  "created_at": "2026-11-20T12:00:00+00:00"
}
```

### Headers

| Header | Purpose |
|---|---|
| `Content-Type` | Always `application/json` |
| `X-EventFlow-Signature` | HMAC-SHA256 signature, format `sha256=<hex>` |
| `X-EventFlow-Delivery` | Unique delivery id, use it to deduplicate |

### Verifying the signature

The signature is computed with your endpoint secret over the **raw request
body bytes**. Do not parse and re-serialize the JSON before checking: key
order and whitespace may change and the signature will not match.

```python
import hashlib
import hmac


def verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    expected = "sha256=" + hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header or "")
```

Always compare with `hmac.compare_digest`, not `==`.

### Responding

- Any `2xx` response means the event was accepted.
- Timeout is 10 seconds.
- Redirects are not followed.

### Retries and deduplication

EventFlow retries on: `408`, `425`, `429`, `500`, `502`, `503`, `504`,
network errors and timeouts. Other `4xx` responses are not retried.

Delay between attempts: 30 s, 60 s, 120 s, then doubling, up to 1 hour.
Maximum 8 attempts. A failed delivery can be retried manually.

Because delivery is at-least-once, store processed `X-EventFlow-Delivery`
values. If the id was already processed, return `200` and do nothing.

### Secret rotation

After `rotate-secret` the old secret stops working immediately. Deliveries
already in the queue are signed with the new secret, so update it on your
side right away.

## Security notes

- Endpoint URLs are validated: only http/https, no credentials, no localhost,
  no private or reserved IP ranges.
- Redirects are disabled when delivering.
- The secret is never returned by regular API calls.

## Project status

Under active development. Planned: dashboard, Docker setup, production
hardening.