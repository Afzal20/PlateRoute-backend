# PlateRoute Backend

Django 6 + DRF modular monolith for a multi-restaurant food-delivery platform
(customer / merchant / courier Flutter clients consume the `/api/v1/` REST
surface generated from the OpenAPI schema at `/api/schema/`).

## Run

```bash
uv sync                       # install deps (uv-managed, package=false)
cp .env.example .env          # then set DJANGO_SECRET_KEY
python manage.py migrate
python manage.py runserver
python manage.py test         # 87 tests
```

## The 18 apps (docs/ARCHITECTURE.md §4)

| App | Owns | Key endpoints (under `/api/v1/`) |
| --- | --- | --- |
| accounts | User, Profile, OTP reset, roles | `/api/auth/*` (register/login/OTP/role) |
| addresses | Address book, GeocodeCache | `addresses/`, `geocode/` |
| vendors | Vendor, Branch, Hours, Staff | `vendors/`, `branches/` |
| menus | Categories, Items, Option groups | `menu/categories/`, `menu/items/` |
| discovery | Read models (no tables) | `restaurants/`, `restaurants/{uuid}/` |
| promotions | Coupons, redemptions | `coupons/validate/` |
| carts | Cart lines, PricingService (pure) | `carts/`, `carts/items/` |
| orders | Order, Items, Events, Idempotency | `orders/place/`, `orders/{uuid}/transition/` |
| payments | Payment, Refund, Ledger, Invoice, Webhooks | `payments/{order}/start/`, `payments/webhooks/{provider}/` |
| delivery | CourierProfile, Tasks, Offers, Pings | `delivery/offers/`, `delivery/tasks/{uuid}/trip/`, `delivery/orders/{uuid}/tracking/` |
| chat | Threads, Participants, Messages | `chat/threads/` |
| calls | CallSession/Event (LiveKit-ready) | `calls/`, `calls/turn-credentials/` |
| notifications | Templates, Outbox, Devices, Prefs | `notifications/devices/`, `notifications/preferences/` |
| reviews | Review, Reply, branch aggregates | `reviews/`, `reviews/branches/{uuid}/` |
| support | Tickets, TicketMessages | `support/tickets/` |
| analytics | Daily branch metrics | `reports/branches/{uuid}/` |
| backoffice | Ops board, refund queue, config | `backoffice/orders|refunds|config/` |
| common | Base models, RuntimeConfig, Outbox, Geo port, errors | `healthz/`, `v1/config/` |

## Conventions

- Money is integer minor units everywhere (DR-005); math lives only in
  `carts/pricing_service.py` and `payments/`.
- Domain events go through the transactional outbox (`OutboxMessage.emit`)
  and are delivered by `manage.py pump_outbox`; other workers:
  `dispatch_sweep` (offer TTL + ping retention), `send_notifications`,
  `rebuild_daily_metrics`.
- Public URLs use non-guessable `uuid` fields (vendors use `slug`).
- Errors: `{detail, code}` envelopes from `common.errors.DomainError`.
- Rate limits run at runtime; they are disabled under `manage.py test`.

## What is intentionally next (per docs/PROJECT_PLAN.md)

- PostgreSQL + Redis + Celery rollout (M1): swap SQLite, move the outbox pump
  to Celery beat, PostGIS when geo queries intensify (lat/lng columns today).
- Channels/Redis WebSocket consumers mirroring REST (`/ws/orders/{uuid}/`,
  `/ws/chat/{thread}/`) — REST truth already exists to mirror.
- Stripe SDK swap for the skeleton gateway + bKash/Nagad adapters (M5/M7).
