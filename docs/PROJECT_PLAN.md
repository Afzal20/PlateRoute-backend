# PlateRoute — Food Delivery Platform
## Project Plan and Requirements Analysis

| Field | Value |
| --- | --- |
| Document | docs/PROJECT_PLAN.md |
| Version | 1.1 |
| Date | 2026-08-27 |
| Revision | 1.0 initial plan; 1.1 added three-client Flutter mobile strategy and related requirements |
| Status | Draft for review |
| Owner | Backend team |
| Applies to | `backend/` Django service and the planned `mobile/` Flutter monorepo |

---

## 1. Executive Summary

PlateRoute is a multi-restaurant food ordering and delivery platform. Customers browse nearby restaurants and menus, build an order, pay online or on delivery, and follow the order live until handover. Restaurants receive, prepare, and hand off orders. Couriers accept pickup and dropoff tasks and navigate between addresses. Platform operators oversee everything from an admin console.

The backend is currently a Django 6 + Django REST Framework monolith with JWT authentication, a custom email-based user model, token-versioned session revocation, OTP-based password reset (hashed, throttled, single-use, branded email), Google SSO entrypoint via allauth, profile management, OpenAPI tooling, and layered rate limiting. This document turns that foundation into a complete product plan: scope, roles, functional and non-functional requirements, domain model, architecture direction, integrations, phased roadmap, test strategy, deployment approach, risks, and open decisions.

Client experience is delivered through three native Flutter applications sharing one codebase organization: a Customer app for ordering and tracking, a Merchant app for restaurant operations, and a Courier app for delivery execution. All three consume the Django REST Framework API described here and are generated against its OpenAPI schema; the operational back office remains web-based inside Django.

## 2. Problem Statement and Goals

### 2.1 Problem statement
Ordering food today involves fragmented tools: phone calls, ad-hoc social media orders, manual dispatch, cash-only reconciliation, and no shared visibility of status between customer, restaurant, and courier. Restaurants lose orders during rush hours, customers have no tracking, and operators have no data.

### 2.2 Product goals
- Provide one reliable channel where demand meets supply: discovery, ordering, preparation, dispatch, delivery, and feedback.
- Keep every party synchronized in real time through explicit order states and notifications.
- Make money movement boring: clear totals, auditable payments, predictable refunds.
- Give operators actionable dashboards covering volumes, prep times, courier utilization, and failures.

### 2.3 Measurable success criteria (first 90 days after pilot launch)
- Order success rate (paid orders completed without support intervention) >= 98 percent.
- Median time from checkout confirmation to restaurant acknowledgment <= 3 minutes.
- Mobile/API p95 latency for core browsing endpoints <= 300 ms at pilot load.
- Zero unresolved charge discrepancies after daily reconciliation runs.
- Deploy safety: migrations reversible, rollback under 15 minutes.

## 3. Stakeholders

| Stakeholder | Interest |
| --- | --- |
| Customers | Fast ordering, transparent pricing, live tracking, safe payments |
| Restaurant owners and staff | Accurate incoming orders, simple menu management, payout clarity |
| Couriers | Clear task queue, fair allocation, earnings visibility |
| Platform operations | Moderation, dispute handling, reconciliation, monitoring |
| Finance | Settlement reports, refunds, tax and VAT records |
| Legal and compliance | Personal data protection, terms of service, consent handling |

## 4. Users, Roles, and Permissions

| Role | Capabilities |
| --- | --- |
| Guest (unauthenticated) | Browse restaurant and menu catalogs, view prices, register or login |
| Customer | Guest abilities plus: manage address book and cart, place orders, pay, track live, cancel within rules, rate completed orders, request refunds |
| Restaurant owner | Manage restaurant profile, menu categories/items/options, opening hours, pricing; accept or reject orders; mark ready |
| Restaurant staff (sub-user) | Same as owner but scoped to their branch/store; cannot edit payout settings |
| Courier | Toggle online status, receive task offers, accept once, progress trip statuses, proof of delivery |
| Dispatcher / operations (staff) | Live board view, manual assignment, override stuck states, resolve disputes |
| Superadmin | Full access including refund approvals, role grants, configuration |

Enforcement model: DRF permission classes plus object-level checks; role resolution from a `role` field on the existing `accounts.User` combined with typed profile rows per role (courier, restaurant owner) instead of ContentTypes permissions, keeping authorization queries simple and indexable.

## 5. Scope Definition

Priorities use MoSCoW: Must (MVP-blocking), Should (ship soon after MVP), Could (later), Won't (explicitly out). Client deliverables are three Flutter applications — Customer, Merchant (restaurant), and Courier — built as one monorepo with shared packages; the platform back office stays web-based in Django.

### 5.1 In scope
1. Authentication, profiles, address book, role onboarding (M)
2. Restaurant catalog and searchable menu with options/modifiers (M)
3. Cart, pricing engine: items, modifiers, delivery fee, VAT, tips, coupons (M)
4. Checkout and order placement with idempotency keys (M)
5. Order lifecycle management for restaurant and courier applications (M)
6. Cash on delivery plus card payment via hosted PSP, Stripe first; bKash/Nagad wallet adapters next (M / Should)
7. Live order status propagation plus push notifications (M)
8. Courier task allocation with nearest-first auto-offer and dispatcher override (M)
9. Ratings and reviews after completion (M)
10. Admin basics: live orders monitor, moderation, refunds workflow (M)
11. Analytics views for operators and restaurant owners (S)

### 5.2 Out of scope for v1
- Scheduled or pre-orders at future time slots
- Group wallets, split payments, buy-now-pay-later
- In-app voice or video calls between parties
- Loyalty points and referral engine
- Subscription billing tiers for restaurants
- Platform-owned dark-store inventory model
- Multi-language UI beyond English with Bengali string infrastructure deferred

## 6. Current System Baseline (Implemented Today)

Working tree on branch `master` includes recent hardening work. Status legend: Done, Partial, Not-started.

| Area | Status | Notes |
| --- | --- | --- |
| Custom user model (email login) | Done | `accounts.User`, unique email, custom manager |
| Registration and login APIs | Done | JWT access/refresh pair, rotation with blacklisting enabled |
| Session revocation machinery | Done | `Profile.token_version` plus `VersionedJWTAuthentication`; bumped on logout-all, re-login, password reset |
| OTP password reset | Done | 8-char mixed alphabet, SHA-256 hashed storage, 15-minute TTL, single-use atomic claim, case-insensitive entry, anti-enumeration responses, throttles (3/hour request, 10/minute confirm), branded HTML/text email, 17 green tests |
| Google SSO redirect entrypoint | Partial | allauth callback wired; needs account-linking polish and testing against real credentials |
| Profile retrieve/update | Done | Email change currently unrestricted; covered by FR-AUTH-05 |
| Rate limiting | Done | Global anon/user defaults, scoped login/register/password-reset throttles, IP middleware cap of 100/minute |
| API documentation | Partial | drf-spectacular wired at `/api/schema`, swagger and redoc; needs per-module tagging |
| Catalog, cart, orders, payments, notifications, analytics | Not started | Planned in phases M2 onward |
| Database | Development only | SQLite file; must move to PostgreSQL before pilot (M1) |
| Background processing | Not started | Celery + Redis planned for emails, dispatch timers, webhooks, aggregates |
| CI/CD, containerization, staging | Not started | Docker compose, pipeline, staging environment land in M1 |

Patterns to carry forward into every new module: environment-driven settings; anonymous endpoints always scoped-throttled; one-time secrets stored hashed rather than raw (as done for OTP); generic detail messages to prevent enumeration; token-version bump on credential-changing events; Django TestCase suites colocated under `tests/`; schema-first documentation.

## 7. Functional Requirements

Requirement IDs follow `FR-<DOMAIN>-<NN>` so tickets can trace back to this document.

### 7.1 Accounts and Authentication (FR-AUTH)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-AUTH-01 | Register with email and strong password; email verification required before first order | M | Partial (registration done, verification pending) |
| FR-AUTH-02 | Login issues short-lived access plus refresh tokens; rotation with blacklisting on refresh remains enabled | M | Done |
| FR-AUTH-03 | Logout from all devices bumps token_version so outstanding JWTs fail validation | M | Done |
| FR-AUTH-04 | Password reset via emailed 8-character OTP, hashed at rest, 15-minute expiry, single-use, case-insensitive entry, throttled per IP | M | Done |
| FR-AUTH-05 | Account email change requires current password and verifies the new address before the swap; password reset also invalidates all sessions | M | Planned |
| FR-AUTH-06 | Google sign-in completion via allauth with profile provisioning; linking to an existing local account only after verified match | S | Partial |
| FR-AUTH-07 | Role onboarding endpoints that attach courier or restaurant owner sub-profiles and activate role permissions | M | Planned |
| FR-AUTH-08 | Address book CRUD per customer: label, receiver name, phone, geo point, delivery notes, default flag; maximum 20 entries | M | Planned |
| FR-AUTH-09 | Account deletion honoring financial record retention while anonymizing personal identifiers | S | Planned |
| FR-AUTH-10 | Per-channel notification preferences stored on profile | S | Planned |

Acceptance criteria samples: unverified users attempting checkout receive a 403 with an actionable message; consecutive wrong OTP confirms from one IP trip the confirm throttle visibly in headers; erased accounts retain invoices without personal identifiers.

### 7.2 Restaurant Catalog (FR-CAT)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-CAT-01 | Restaurant profile CRUD: name, description, cuisines, logo and cover images, address, geo point, opening-hours matrix, minimum order value, prep time, status draft/pending/approved/paused/closed | M | Planned |
| FR-CAT-02 | Approval workflow: superadmin approves new restaurants before public visibility | M | Planned |
| FR-CAT-03 | Menu tree per restaurant: ordered categories, items with images, description, base price, availability toggle | M | Planned |
| FR-CAT-04 | Option groups per item (size, addons, extras) with min/max selection rules and price deltas; invalid combinations rejected at add-to-cart time | M | Planned |
| FR-CAT-05 | Search and discovery: text search over name/cuisine/tags, filters for open-now, sorting by distance/rating/price, geo-ranked results when location supplied | M | Planned |
| FR-CAT-06 | Redis caching of hot catalog reads with signal-driven invalidation; ETag support on public lists | S | Planned |
| FR-CAT-07 | Bulk menu import/export parsed by background workers | C | Planned |

Catalog is intentionally price-change aware everywhere downstream: cart lines and orders store snapshots so later edits never retroactively alter placed history.

### 7.3 Cart and Pricing (FR-CART)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-CART-01 | Server-side cart per customer scoped to one restaurant; adding from another restaurant requires explicit replace-or-separate decision | M | Planned |
| FR-CART-02 | Line items snapshot item title, unit price, chosen options, quantity; edits revalidate against menu reference ids and reject unavailable changes | M | Planned |
| FR-CART-03 | Single pricing service shared by cart preview, checkout quote, and order creation producing subtotal, coupon discount, delivery fee zone formula, small-order fee, tips, VAT breakdown line by line | M | Planned |
| FR-CART-04 | Coupons of percent/fixed/free-delivery kinds with validity window, global and per-user redemption caps, minimum basket; atomic redemption inside checkout transaction to prevent double-spend | M | Planned |
| FR-CART-05 | Checkout truthfulness: quotes older than a configurable TTL return a fresh quote and require client reconfirmation before charge | M | Planned |

All money math uses integer minor units end to end; rounding rules are documented in the pricing service docstring and covered by property-based tests (totals always equal sum of parts, never negative).

### 7.4 Orders and Lifecycle (FR-ORD)

Canonical happy path: `PLACED -> ACCEPTED -> PREPARING -> READY_FOR_PICKUP -> PICKED_UP -> OUT_FOR_DELIVERY -> DELIVERED`.

Side exits from allowed origins: `REJECTED` (restaurant), `CANCELLED_CUSTOMER`, `CANCELLED_RESTAURANT`, `CANCELLED_PLATFORM` (dispatcher), `FAILED_PAYMENT`, `REFUND_PENDING -> REFUNDED`. A server-side state machine validates every transition, records actor type and id, timestamp, reason code, and payload snapshot into an append-only `OrderEvent` audit table. Illegal transitions raise domain errors rather than being silently coerced.

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-ORD-01 | Place order atomically: validate cart, freeze price snapshot, create order plus items plus initial event, start restaurant accept-timer that auto-cancels after a configured grace period | M | Planned |
| FR-ORD-02 | Idempotent creation via client-supplied Idempotency-Key stored per customer; replays return the original outcome without side effects | M | Planned |
| FR-ORD-03 | Restaurant accept/reject with mandatory reason codes on rejection; rejection triggers refund or void according to capture mode | M | Planned |
| FR-ORD-04 | Customer cancellation rules per elapsed stage: free pre-ACCEPTED, fee-bracketed until PICKED_UP, support-ticket-only afterwards | M | Planned |
| FR-ORD-05 | Every transition fans out realtime updates to authorized parties and writes the immutable OrderEvent row in the same transaction boundary | M | Planned |
| FR-ORD-06 | Object permissions: order readable only by its customer, assigned courier, owning restaurant staff, and operators | M | Planned |
| FR-ORD-07 | Paginated order history with status/date filters and CSV export for owners and operators | S | Planned |
| FR-ORD-08 | Dispatcher overrides: forced transitions with mandatory reasons, reopening disputed deliveries, rescheduling refunds | S | Planned |

### 7.5 Delivery and Courier Operations (FR-DLV)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-DLV-01 | On READY_FOR_PICKUP create a DeliveryTask capturing pickup geo point, dropoff address snapshot, promised SLA, courier fee, and tip split | M | Planned |
| FR-DLV-02 | Allocation loop offers the task to nearest online couriers respecting capacity; offers expire after T seconds and cascade outward; dispatcher may force-assign at any time | M | Planned |
| FR-DLV-03 | Courier flow: go online with vehicle record, receive offer payloads, atomic single-winner claim, trip statuses mapped to order events, optional proof-of-delivery photo or door code | M | Planned |
| FR-DLV-04 | Location telemetry: batched coordinate posts every 10 to 20 seconds while on an active task; latest position feeds ETA; history pruned after 30 days | M | Planned |
| FR-DLV-05 | Earnings ledger per courier: per-drop base, distance bonus, tips, deductions, payout cycle exports | S | Planned |
| FR-DLV-06 | Route and ETA display via provider directions API with graceful degradation to straight-line haversine estimate when quota exhausted | S | Planned |

### 7.6 Payments and Refunds (FR-PAY)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-PAY-01 | Gateway abstraction interface: authorize, capture, void, refund, verify-webhook; Stripe is the first adapter and COD is modeled as a pseudo-gateway feeding the same ledger | M | Planned |
| FR-PAY-02 | Card data handled exclusively by PSP-hosted elements; servers store only PSP token plus brand and last4 metadata; no PAN ever touches the platform | M | Planned |
| FR-PAY-03 | Webhook receivers validate HMAC signatures, deduplicate by event id, enqueue worker processing, and respond quickly | M | Planned |
| FR-PAY-04 | bKash and Nagad wallet adapters behind the same interface with per-environment sandbox toggles | S | Planned |
| FR-PAY-05 | Refund workflow: full or partial, reason-coded, operator approval above threshold, executed by worker, visible on order timeline | M | Planned |
| FR-PAY-06 | Daily reconciliation job comparing internal ledger against gateway settlement report; mismatches raise operator alerts | S | Planned |
| FR-PAY-07 | VAT computed from regulatory configuration with printable invoice numbers issued on completion | M | Planned |

Payment states are owned exclusively by the worker processing gateway events; API responses reflect state read-only so webhook races cannot corrupt totals.

### 7.7 Notifications (FR-NOT)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-NOT-01 | Transactional email through a provider adapter, keeping the console backend for local development; templates are version-controlled like the OTP email | M | Partial (OTP email shipped) |
| FR-NOT-02 | Push notifications: FCM device registry per user; order events, task offers, and preference-aware promotions; silent data messages drive courier app refreshes | M | Planned |
| FR-NOT-03 | Realtime per-order channel using Django Channels over Redis delivering state-machine events only to authorized sockets | M | Planned |
| FR-NOT-04 | SMS fallback for critical OTP-class actions when email deliverability is poor | S | Planned |
| FR-NOT-05 | In-app notification center with read and unread state | S | Planned |

### 7.8 Reviews, Support, Trust (FR-RVW)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-RVW-01 | One review per completed order rating the restaurant plus optional courier stars with length-capped body text | M | Planned |
| FR-RVW-02 | Restaurant replies allowed on reviews; moderation hide action leaves an audit trail | S | Planned |
| FR-RVW-03 | Rating aggregates (average, histogram) maintained via signals, not computed on read | M | Planned |
| FR-RVW-04 | Support tickets linkable to orders with status trail and aging SLA surfaced to operators | S | Planned |

### 7.9 Administration and Back Office (FR-ADM)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-ADM-01 | Django admin registration for all new models following the existing User/Profile/PasswordResetOTP pattern with list displays, filters, search, readonly sensitive fields | M | Planned |
| FR-ADM-02 | Operations dashboard: live orders board, courier map feed, failure and refund queues | M | Planned |
| FR-ADM-03 | Runtime configuration (default fees, accept-timeout, offer-expiry, service radius) editable without redeploy and cached with short TTL | M | Planned |
| FR-ADM-04 | Audit log of privileged mutations: role grants, refund approvals, menu deletions, config changes | M | Planned |

### 7.10 Reporting and Analytics (FR-REP)

| ID | Requirement | Priority | Status |
| --- | --- | --- | --- |
| FR-REP-01 | Operator KPIs: GMV, AOV, completion rate, cancellation reason distribution, courier utilization, prep-time percentiles over time | S | Planned |
| FR-REP-02 | Restaurant portal reports: sales by daypart and item, top items, rating trend, cancellation causes | S | Planned |
| FR-REP-03 | Nightly aggregation into summary tables executed by Celery beat so dashboards read cheap aggregates instead of raw orders | S | Planned |

## 8. Mobile Applications (Flutter)

### 8.1 Client Platform Overview

| App | Audience | Primary jobs | Distribution |
| --- | --- | --- | --- |
| Customer | Diners ordering food | Discover, order, pay, track live, review, manage profile and addresses | Public app stores from pilot launch |
| Merchant (restaurant) | Owners and staff | Menu management, incoming-order alarms with accept SLA, status progression, payouts view | Public stores after pilot whitelisting; Firebase App Distribution during build-out |
| Courier | Delivery riders | Shift toggle, task offers with countdown claim, navigation handoff, trip statuses, proof of delivery, earnings | Private channel during pilot, stores after fleet onboarding |

All three apps are thin shells over a shared Dart monorepo: `packages/api_client` is generated from the backend OpenAPI schema in CI, `packages/core_ui` carries the design system, and per-domain feature packages prevent copy-paste drift between apps. Builds are configured through flavors (`dev`, `stg`, `prod`) selecting API base URLs, Firebase projects, and crash-reporting targets. Supported device floor at launch: Android 8.0 (API 26) and iOS 14.

Recommended stack decisions (revisit only via ADR):

| Layer | Choice |
| --- | --- |
| Framework | Flutter stable channel, Dart sound null safety |
| State and DI | Riverpod with code generation |
| Routing and deep links | go_router with universal links / app-scheme handlers |
| Networking | Generated Dart client (OpenAPI generator, dart-dio template) wrapped by dio interceptors adding bearer auth, Idempotency-Key, and X-App-Version headers |
| Secrets and tokens | flutter_secure_storage (Keychain / Keystore backed) |
| Push | firebase_messaging plus flutter_local_notifications |
| Maps and location | google_maps_flutter, geolocator, permission_handler |
| Payments | Stripe Flutter SDK sheet; wallet redirects until bKash/Nagad switches ship |
| Observability | sentry_flutter release-tagged crashes and performance traces |
| Localization | intl with ARB files, en default and bn included |
| CI distribution | GitHub Actions or Codemagic lanes per flavor; Firebase App Distribution for Android and TestFlight for iOS testers |

OS-level prerequisites treated as requirements, not chores: purpose strings and manifest permissions for camera, photo library, notifications, and (Courier only) background location; store privacy disclosures drafted alongside feature work rather than at submission time.

### 8.2 Common Mobile Requirements (MOB-C)

Applies to all three apps unless noted.

| ID | Requirement | Priority |
| --- | --- | --- |
| MOB-C-01 | Authentication lifecycle over existing endpoints: login, register, OTP password reset entry; tokens persisted only in secure storage; silent refresh with queued requests on 401; token_version invalidation lands the user back on login with a clear message | M |
| MOB-C-02 | FCM token upsert to the device registry endpoint; notification rendering foreground and background; tap-through routing by payload type (order, task, promo-preference aware) | M |
| MOB-C-03 | Deep links and universal links resolving to order tracking, password reset continuation, and merchant order board screens; scheme plus associated-domain configuration shipped per flavor | M |
| MOB-C-04 | Every mutating call sends an Idempotency-Key header; retries after network failure never duplicate payments or claims | M |
| MOB-C-05 | Unified error mapping: DRF field errors and `{detail}` responses translated into localized human messages with field anchoring where applicable | M |
| MOB-C-06 | Offline posture: read caches with explicit stale banners and pull-to-refresh; Courier-only offline queue for location writes flushed on connectivity return | M (cache) / S (queue elsewhere) |
| MOB-C-07 | Shared infinite-scroll list components compatible with offset pagination now and cursor feeds later | M |
| MOB-C-08 | Localization en/bn from first release through ARB pipeline; layouts verified against bn string expansion | M |
| MOB-C-09 | Analytics event catalog mirroring backend business counters (placement, acceptance latency, claim acceptance) feeding both funnels | S |
| MOB-C-10 | Sentry integration release-tagged; cold-start and jank traces enabled in stg builds | M |
| MOB-C-11 | Accessibility baseline: dynamic type scaling without clipping, WCAG AA contrast for primary flows | S |
| MOB-C-12 | Force-update policy: apps fetch minimum supported versions from the backend runtime-config service; below soft floor shows dismissible banner, below hard floor blocks usage with store link | M |
| MOB-C-13 | Account deletion and data-export request path reachable from profile settings (backend FR-AUTH-09) | S |
| MOB-C-14 | Store metadata kit maintained continuously: screenshot pipelines per device class, Play Data Safety and Apple privacy labels kept truthful per release | M |

Cross-cutting rule: any capability the client needs that the API lacks is raised as a backend ticket under contract-first discipline before UI work proceeds past a stub; generated-client compilation against `main` acts as the compatibility gate.

### 8.3 Customer App Requirements (MOB-USR)

| ID | Requirement | Priority | Backend FRs consumed |
| --- | --- | --- | --- |
| MOB-USR-01 | Onboarding: sign up, email verification gating notice, login, OTP password reset flow with branded context | M | FR-AUTH-01..04 |
| MOB-USR-02 | Home discovery feed using device location with permission pre-prompt rationale; category rails and open-now filter | M | FR-CAT-05 |
| MOB-USR-03 | Restaurant and menu browsing with option-group selector enforcing min/max rules client-side alongside server validation | M | FR-CAT-03/04 |
| MOB-USR-04 | Cart interactions including cross-restaurant conflict dialog per replace-or-separate policy | M | FR-CART-01/02 |
| MOB-USR-05 | Checkout: quote display with TTL reconfirmation, Stripe payment sheet, COD selection when eligible, coupon entry | M | FR-CART-03/04/05, FR-PAY-01/02 |
| MOB-USR-06 | Live tracking screen: map with courier marker, ETA chip, WebSocket updates with poll fallback on socket loss | M | FR-NOT-03, FR-DLV-04 |
| MOB-USR-07 | Order timeline listing OrderEvent history for transparency | M | FR-ORD-05 |
| MOB-USR-08 | Address book manager with default selection and map-pin placement | M | FR-AUTH-08 |
| MOB-USR-09 | Review composer after DELIVERED with star entry and length-capped text | M | FR-RVW-01 |
| MOB-USR-10 | Profile security center: active sessions indicator, change password via OTP flow, notification preference toggles | S | FR-AUTH-04/10 |
| MOB-USR-11 | Search with persisted filter and sort preferences across sessions | M | FR-CAT-05 |
| MOB-USR-12 | Order-issue report form creating a support ticket linked to the order | S | FR-RVW-04 |

### 8.4 Merchant App Requirements (MOB-RST)

| ID | Requirement | Priority | Backend FRs consumed |
| --- | --- | --- | --- |
| MOB-RST-01 | Onboarding showing approval pipeline states pending/approved/paused so owners understand visibility status | M | FR-CAT-01/02 |
| MOB-RST-02 | Menu manager: categories, items, option groups CRUD with direct-to-bucket photo uploads via signed URLs | M | FR-CAT-03/04 |
| MOB-RST-03 | Availability toggle switches syncing immediately with stock-out behavior | M | FR-CAT-03 |
| MOB-RST-04 | Incoming-order alarm: full-screen persistent ring until acknowledged; reject requires structured reason codes | M | FR-ORD-01/03 |
| MOB-RST-05 | Accept SLA countdown visual aligned to backend auto-cancel timer | M | FR-ORD-01 |
| MOB-RST-06 | Status progression controls guarded by allowed transitions only (PREPARING then READY_FOR_PICKUP) | M | FR-ORD state machine |
| MOB-RST-07 | Historic order list with filters and CSV export request trigger | S | FR-ORD-07 |
| MOB-RST-08 | Payout ledger read-only view of periods, gross, commission, net | M | PayoutLedger, FR-PAY settlement |
| MOB-RST-09 | Review reply composer from rating detail screens | S | FR-RVW-02 |
| MOB-RST-10 | Store-health checklist nudges: missing images, uncovered hours, long prep estimates | S | FR-CAT-01 |

Merchant acceptance reliability is a product gate: alarm rendering must survive killed-app state via FCM high-priority data messages plus local-notification fallback, verified in device-matrix tests.

### 8.5 Courier App Requirements (MOB-CUR)

| ID | Requirement | Priority | Backend FRs consumed |
| --- | --- | --- | --- |
| MOB-CUR-01 | Shift console: online/offline toggle with vehicle check snapshot recorded | M | FR-DLV-02/03, CourierProfile |
| MOB-CUR-02 | Task offer card with expiry countdown and atomic accept-once action surfaced on both push tap and list | M | FR-DLV-02/03 |
| MOB-CUR-03 | Navigation handoff deep links into Google or Apple Maps per trip leg with in-app fallback route preview | M | FR-DLV-06 |
| MOB-CUR-04 | Trip progress buttons mapped exactly to allowed delivery transitions with arrival geofence hints near pickup and dropoff | M | FR-DLV-03 |
| MOB-CUR-05 | Foreground-service location streaming during accepted tasks, offline queueing when signal drops, visible privacy indicator at all times while active | M | FR-DLV-04, NFR-16 |
| MOB-CUR-06 | Proof-of-delivery capture: photo plus optional door-code entry depending on task configuration | M | FR-DLV-03 |
| MOB-CUR-07 | Earnings screen: today and period breakdowns of base, bonuses, tips, deductions | S | FR-DLV-05 |
| MOB-CUR-08 | Battery-aware ping interval presets configurable by operations through runtime config rather than app release | S | FR-ADM-03 |

Contract mapping note: every client table cites the backend FRs it consumes. When implementation order differs (for example customer tracking landing before PostGIS-backed ETAs), the cited FR defines the agreed interface and temporary behavior is flagged in the API as experimental fields rather than silent divergence.

## 9. Domain Model Outline

Entities extend the existing accounts core (`User`, `Profile` with `token_version`, `PasswordResetOTP`). Only defining fields are listed; migrations will formalize constraints.

Identity and access
- `EmailVerification(user, token_hash, expires_at)` for FR-AUTH-01/05
- `Address(user FK, label, receiver_name, phone, geo_point, directions, is_default)`
- Typed profiles: `RestaurantOwnerProfile`, `CourierProfile(vehicle_type, plate, is_online, last_seen_at)` referenced through `User.role`

Catalog
- `Restaurant(owner FK, name, slug, description, cuisines M2M, logo, cover, geo_point, address_text, open_hours JSONB, min_order_amount, prep_minutes, commission_pct, status)`
- `MenuCategory(restaurant FK, name, position)`
- `MenuItem(category FK, name, description, image, base_price, available)`
- `OptionGroup(menu_item FK, title, min_select, max_select)` and `Option(group FK, label, price_delta)`
- `Coupon(code unique, kind, value, starts_at, ends_at, max_redemptions, per_user_limit, min_basket, active)`

Ordering
- `Cart(user 1-1, restaurant FK nullable)` and `CartItem(cart FK, menu_item_ref, quantity, selected_options JSONB, unit_price_snapshot)`
- `Order(customer FK, restaurant FK, status, currency, items_total, discount_total, delivery_fee, vat_total, tip_total, grand_total, address_snapshot JSONB, idempotency_key unique, placed_at, eta_snapshot, cancelled_reason_code nullable)`
- `OrderItem(order FK, menu_item_ref, title_snapshot, unit_price_snapshot, quantity, options_snapshot JSONB)`
- `OrderEvent(order FK, from_status, to_status, actor_type, actor_id, reason, payload JSONB, created_at)` append-only
- `DeliveryTask(order 1-1, courier FK nullable, pickup_geo, dropoff_geo, state, offered_at, accepted_at, picked_up_at, delivered_at, courier_fee)` plus `DeliveryOffer(task FK, courier FK, expires_at, state)`
- `LocationPing(courier FK, order FK nullable, geo_point, recorded_at)` pruned after retention window

Money
- `Payment(order 1-1, gateway, gateway_reference unique, amount_minor, currency, state, brand_last4 nullable)`
- `Refund(payment FK, amount_minor, reason_code, state, requested_by, approved_by, processed_at)`
- `PayoutLedger(payee_user FK, period_start, period_end, gross_minor, commission_minor, net_minor, state, settled_at)`

Trust and operations
- `Review(order 1-1, restaurant_stars, courier_stars, body)` with `ReviewReply(review FK, author, body)`
- `DeviceRegistry(user FK, fcm_token unique, platform, last_used_at)`
- `SupportTicket(order FK nullable, opened_by FK, category, priority, status)`
- `AuditLog(actor_user FK, action, target_model, target_id, diff JSONB, created_at)`
- `RuntimeConfig(key unique, value JSONB, updated_by, updated_at)` backing FR-ADM-03

Index plan established with the first migrations: composite `(customer_id, status, placed_at)` on Order; trigram or GIN index on Restaurant.name for search; partial index on unpaid orders; GiST geospatial indexes once PostGIS lands in M4; unique partial index on active carts per user.

## 10. Non-Functional Requirements

| ID | Category | Requirement |
| --- | --- | --- |
| NFR-01 | Performance | Catalog browse p95 <= 300 ms; cart quote p95 <= 400 ms; order placement p95 <= 700 ms at 200 rps sustained |
| NFR-02 | Scalability | Stateless app tier scaled horizontally behind a load balancer; hot reads from Redis; pooled DB connections via PgBouncer |
| NFR-03 | Availability | At least 99.5 percent monthly for ordering paths; graceful degradation serving cached menus during dependency outages |
| NFR-04 | Consistency | Money handled in integer minor units inside transactions with select_for_update on contested rows |
| NFR-05 | Idempotency | Mutating client calls accept idempotency keys; gateway webhooks deduplicate by event id |
| NFR-06 | Security | OWASP alignment; secrets only from environment; TLS everywhere; HMAC on webhooks; ORM-only data access; existing security headers and throttles retained and extended per module |
| NFR-07 | Fraud control | Velocity limits per device/IP/account, hashed one-time codes for sensitive confirmations, dispatcher review queue for anomalous cancellation patterns |
| NFR-08 | Privacy | Export and erasure endpoints for personal data; PII minimized in logs (masking helper already introduced with OTP logging) |
| NFR-09 | Observability | Structured JSON logs with request-id correlation, Sentry exception tracking, business metrics per order transition alongside latency metrics |
| NFR-10 | Maintainability | CI-gated test suite (baseline exists), coverage >= 80 percent for domain logic packages, expand-contract migration discipline |
| NFR-11 | Compatibility | OpenAPI schema published continuously through drf-spectacular; clients generated from spec |
| NFR-12 | Localization | en/bn locale scaffolding with timezone-aware timestamps (USE_TZ already true) |
| NFR-13 | Retention | Location pings 30 days; application logs 90 days; financial records 7 years; personas soft-deleted after erasure |
| NFR-14 | Device support | Android 8.0+ / iOS 14+ floor; cold start to interactive <= 2 seconds on mid-tier hardware; release APK <= 40 MB |
| NFR-15 | Version skew | Backend keeps at least one minor backward-compatible window per breaking change; apps enforce soft/hard minimums fetched from runtime config (MOB-C-12) |
| NFR-16 | Location privacy | Background location exists only in the Courier app with explicit purpose strings, user opt-in, persistent visibility indicator, and retention per NFR-13 |
| NFR-17 | Store compliance | Play Data Safety forms and Apple privacy nutrition labels accurate every submission; no ad identifiers in builds |

## 11. Target Architecture

Monolith-first with modular apps mirroring bounded contexts so future extraction stays cheap. Clients talk to REST under `/api/v1/` plus WebSocket channels for live events.

```
Clients: 3 Flutter apps - Customer | Merchant (restaurant) | Courier
         shared monorepo packages: generated api_client, core_ui
         Web back office remains Django-based (admin + ops dashboards)
                    REST /api/v1 (JWT, X-App-Version)   +   WS /ws
                              |
                     Load balancer / WAF
                              |
        Django monolith: gunicorn (HTTP) + asgi (channels)
   apps: accounts(done) | catalog | carts | pricing | orders
         | delivery | payments | notifications | reviews
         | support | analytics
                              |
     PostgreSQL (+PostGIS later)    Redis (cache, celery broker,
                                       channels layer)
                              |
   Celery workers + beat: emails, push fanout, dispatch timers,
        webhook processing, reconciliation, nightly aggregates
                              |
External: Stripe | bKash | Nagad | FCM | SMS gateway | Maps/Directions
          | S3 media bucket | Sentry
```

| Concern | Today | Target |
| --- | --- | --- |
| Database | SQLite dev file | PostgreSQL 16; PostGIS types when geo queries intensify |
| Cache, locks, channels layer | LocMem | Redis |
| Async jobs | Inline request-time email | Celery workers plus beat schedules |
| Mail backend | Console locally, SMTP configurable | Transactional provider in staging/prod using the existing settings seam |
| Geo storage | None | Decimal lat/lng first, PostGIS when justified |
| Media | Local dev | S3-compatible bucket with signed direct uploads |
| Documentation | drf-spectacular root endpoints | Per-module tag groups with examples, published in CI |
| Client tier | None yet | Flutter stable monorepo, three flavored apps over generated Dart `api_client` package |

API conventions: URL-versioned `/api/v1/`; DRF-standard error envelopes `{field: [messages]}` plus `{detail}` for non-field errors matching current endpoints; `LimitOffsetPagination` page size 50 as configured today; cursor pagination reserved for high-churn feeds like courier location streams; bearer JWT authentication with token_version enforcement carried over unchanged. Mobile clients additionally send an `X-App-Version` header logged for cohort analysis; deprecation warnings ride response headers before removals so older builds surface upgrade banners via runtime config rather than silent breakage.

## 12. Third-party Integrations

| Integration | Purpose | Notes |
| --- | --- | --- |
| Stripe | Cards and wallets, refunds | Signature-verified webhooks, test clocks in staging, idempotent event processing |
| bKash / Nagad | Local wallet checkout | Sandbox toggles per environment; retry-safe token refresh inside adapter |
| Firebase Cloud Messaging | Push to customer and courier devices | Token registry plus role topics; silent data messages for couriers |
| SMS gateway | Critical fallback notices | Shared outbox abstraction alongside email adapter |
| Maps / Directions provider | Geocoding, autocomplete, routes, ETA | Aggressive caching of geocode results; spend budget monitoring with haversine fallback; client map UI via google_maps_flutter |
| S3-compatible storage | Menu images, delivery proofs | Signed direct uploads from clients; scan hook on proof uploads |
| Sentry | Error tracking | Release-tagged issues routed to on-call |
| Firebase App Distribution / TestFlight | Pre-release builds to testers | Per-flavor artifact uploads from CI with release notes tied to roadmap milestones |

All third-party adapters live behind internal interfaces (`PaymentGateway`, `Notifier`, `GeoRouter`) so vendor swaps never touch domain code.

## 13. Delivery Roadmap

Phases sized in sprints for one senior backend developer with frontend workstreams running in parallel. Exit criteria are hard gates; the next phase does not start until they hold.

| Phase | Name | Content | Exit criteria |
| --- | --- | --- | --- |
| M0 | Foundation | Already shipped: email auth, JWT session revocation, OTP reset with branded mail, throttling layers, schema tooling, green test baseline | Met today |
| M1 | Platform readiness | PostgreSQL plus Redis plus Celery rollout, Docker compose, CI running tests, staging deploy, transactional email cutover, email verification endpoint (FR-AUTH-01 remainder), Flutter monorepo scaffold with generated `api_client` package wired into CI | Staging deploys from a green pipeline; verification flow passes end to end; Dart client compiles against current schema in CI |
| M2 | Catalog | Restaurant onboarding and approvals, menu and options CRUD, media to bucket, search, catalog caching (FR-CAT all); merchant app ships menu manager and order board modules | Two seeded restaurants browsable through API with sub-second cached reads; merchant app performs a full menu-edit round trip on staging |
| M3 | Ordering core | Addresses, cart, pricing service, coupons, idempotent checkout, order state machine with events, restaurant accept console endpoints (FR-CART, FR-ORD-01..07) | Happy-path order reaches READY_FOR_PICKUP with exact money math and full audit trail; customer app completes quote-and-reconfirm checkout end to end against staging |
| M4 | Fulfillment | Delivery tasks, courier endpoints, allocation loop, location ingestion, Channels-based tracking, FCM wiring (FR-DLV-01..04, FR-NOT-02/03) | Courier app completes pickup and dropoff while customer watches live movement |
| M5 | Money | Stripe integration and COD ledger, webhooks, refunds workflow, VAT invoices, reconciliation skeleton (FR-PAY) | Paid, refunded, and COD orders reconcile clean for one week in staging |
| M6 | Trust and launch | Reviews, notification center, dispatch dashboard v1, runtime config service (powering MOB-C-12 force-update floors), load testing, penetration-test fixes, UAT (remaining Must items) | Pilot go-live checklist signed off by operations; app-store submissions approved or pilot whitelisting active for all three apps |
| M7 | Growth wave | bKash/Nagad adapters, reporting portals, bulk menu import, scheduled-order evaluation, bn localization | Backlog driven, no gate |

Sequencing notes: payments work enters shadow mode during M4 to de-risk M5; PostGIS adoption is evaluated at M4 exit rather than assumed upfront; every phase updates this document's status columns as part of its definition of done. Client shells start early on shared packages so app parity grows alongside backend phases instead of trailing them; the merchant shell shadows M2 flows against staging before its modules ship, and the customer shell does the same during M3.

## 14. Test Strategy

- Layers: pure-unit tests for domain services (pricing calculator, state machine guards) independent of HTTP; Django integration tests following the established `manage.py test tests` pattern for serializers, permissions, and transitions; a live-server external smoke script already exists and grows per module; Playwright end-to-end journeys on the web console (register, order, pay, review) against staging.
- Data: factory_boy with deterministic seeds; property-based tests for pricing invariants (parts sum to totals, no negative amounts, documented rounding).
- Explicit concurrency cases: duplicate checkout with one idempotency key, simultaneous courier claims on a single task, refresh-token reuse after rotation, OTP claim racing between two requests.
- Environments: ephemeral in-memory test database through the existing runner; staging dataset refreshed weekly from anonymized snapshots.
- CI gates: full suite green, coverage threshold met, OpenAPI schema renders without errors, no migration drift via `makemigrations --check`, dependency and static security scans.
- Mobile tiers: Dart unit tests for state containers and mappers; widget tests per screen contract; integration_test journeys (login, checkout, task claim, trip completion) run nightly on an emulator matrix across the supported device floor; golden snapshots for core screens per flavor.
- Contract sync between sides: regenerated Dart `api_client` must compile in client CI on every schema change; breaking diffs fail both pipelines unless the documented deprecation window is honored (NFR-15).
- Release gates: accessibility pass on consoles, transactional email snapshots verified against major clients before shipping template changes.

## 15. Deployment and Operations

- Environments: local Docker compose running app, postgres, redis, worker, beat, and mailpit; minimal staging mirroring production shape; hardened production.
- Configuration stays environment-driven as today; `.env.example` updated per change; secret scanning in CI prevents credential commits.
- Deploys use immutable images tagged with git sha; migrations run as a pre-deploy job under expand-contract discipline so any release rolls back without data loss.
- Health endpoints: `/healthz` liveness and `/readyz` readiness probing database and redis.
- Scheduled work lives exclusively in Celery beat: dispatch timers, telemetry pruning, reconciliation, nightly aggregates; each emits heartbeat metrics.
- Incident hooks: Sentry severity routing plus alert rules for business anomalies such as accept-timer breach rate, webhook backlog depth, or refund queue age.
- Mobile release train: weekly builds cut from a protected main behind flavor flags; staged rollout percentages on stores with automatic halt when crash-free sessions drop below 99.5 percent; hard-force-update floors let ops retire broken builds quickly; payment-blocking hotfixes ride outside the train.

## 16. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Pricing or coupon concurrency defects leaking revenue | High | Single pricing service, transactional locks, integer minor units, property tests, idempotent checkout |
| Realtime tracking costs (battery, bandwidth, server) | Medium | Batched pings with stage-adaptive intervals, tuned channels layer, payload pruning |
| Payment provider outage blocks checkout at peak | High | Circuit breaker per gateway, COD fallback messaging, queued webhook retries with dead-letter inspection tooling |
| Courier liquidity shortfall during lunch rush | High | Zone-tuned offer cascades, dispatcher war-room view, configurable incentive levers |
| Email deliverability degradation breaking OTP reset | Medium | Reputable provider with SPF/DKIM alignment, SMS fallback requirement FR-NOT-04, worker retries with backoff |
| Scope creep before launch | Schedule risk | MoSCoW freeze where the Must list defines MVP; new ideas enter the M7 backlog only |
| SQLite-only query assumptions surfacing late | Rework risk | M1 makes PostgreSQL the default before order-heavy code lands; CI runs against real PostgreSQL |
| Solo-developer knowledge concentration | Process risk | This living plan plus architecture decision records; infrastructure expressed as code for fast rebuilds |
| App-store review rejections delaying launch windows | High | Submit three weeks ahead with complete privacy disclosures; distribute pilot builds via App Distribution and TestFlight meanwhile |
| Schema churn breaking shipped mobile versions | High | Generated Dart client compiled in both CIs, semantic versioning, response-header deprecations, hard force-update floors (MOB-C-12, NFR-15) |
| iOS background-location entitlement rejection | Medium | Courier-only purpose strings, default to while-in-use permission with explicit upgrade prompt, entitlement audit each release |
| Plugin and SDK drift across three Flutter apps | Medium | Centralized dependency bumps in shared packages, monthly upgrade ritual, pinned versions owned by one maintainer role |

## 17. Open Decisions Required

1. Courier model: employed fleet, freelance marketplace, or hybrid; drives FR-DLV-05 ledger design and onboarding verification depth.
2. Pilot payment mix: is cash on delivery mandatory on day one or card and wallet first in a limited city?
3. Restaurant contracting terms: flat commission percent versus tiered versus delivery-fee pass-through; affects payout ledger formulas.
4. Coverage definition: operations-drawn zone polygons versus computed drive-time service areas.
5. VAT percentages and invoice numbering rules per jurisdiction to finalize FR-PAY-07.
6. Tip policy: pooling legality and courier payout timing, instant versus weekly cycles.
7. Launch locale scope: English only with Bengali strings deferred to M7, or dual language from day one.
8. Multi-restaurant pooled baskets remain out of v1 unless product overrides (recommendation: out).
9. Confirm the mobile device floor (proposal Android 8.0 and iOS 14) balancing field-device reality against background-location UX targets.
10. Payment UX path: native Stripe sheet plus hosted wallet redirects now, or waiting for certified bKash/Nagad app-switch flows before exposing wallet buttons.

## 18. Glossary

- **AOV** Average Order Value
- **COD** Cash on Delivery
- **DLQ** Dead Letter Queue for failed asynchronous jobs
- **GMV** Gross Merchandise Value transacted
- **Idempotency Key** Client-supplied token guaranteeing a repeated request applies once
- **KYC** Know Your Customer verification for merchants and couriers
- **OTP** One-Time Passcode, as shipped today for password reset
- **POV** Proof of Delivery artifact captured by couriers (photo or door code)
- **PSP** Payment Service Provider
- **SLA** Service Level Agreement or time promise
- **UAT** User Acceptance Testing
- **Flavor** Build-time environment variant wiring bundle id, API base URL, and Firebase project per environment
- **AAB** Android App Bundle, store upload format
- **Version Skew** The mismatch window between released app versions and deployed API capabilities

---

Living document. Requirement status columns and roadmap exit criteria are updated as phases land; every architecture-affecting decision gets an ADR referenced from here.