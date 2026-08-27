# Merchant App — UI Design Instructions

| Field | Value |
| --- | --- |
| Document | docs/design/MERCHANT_APP_UI.md |
| Version | 1.0 |
| Date | 2026-08-27 |
| Owner | Design lead |
| Related | PROJECT_PLAN.md sections 8.4 and 13, ARCHITECTURE.md sections 5-6 and 10 |

---

## 1. Who we are designing for

The merchant does not browse an app; they run a kitchen inside one. Staff stand in heat and noise with wet or greasy hands while oil spits and three people shout. Sessions are long all day but attention comes in two-second slices between tasks. The phone may sit propped against a pillar at arm's length.

| Persona snapshot | Context | Emotional driver | Design answer |
| --- | --- | --- | --- |
| Fatema, owner-manager | Jumps between ledger notebook and stove; fears losing money to platform opacity | Control and fairness | Payout math visible without asking; every fee line reconcilable |
| Rafi, dinner-rush staff | Handles 40 orders an hour peak; phone face-down until alarm fires | Fear of missing or double-handling an order | Alarms that survive anything; acceptance in under 7 seconds with muscle memory |
| New joiner first week | Unsure which button is safe | Fear of irreversible mistakes | Destructive paths structurally slower than productive ones; no hidden actions |

Core insight: speed here is not convenience, it is money — an SLA breach auto-cancels the order (FR-ORD-01) so the interface must convert alert into accepted state faster than the user can read this sentence twice.

## 2. Experience principles

1. Glance-first. Every screen answers "what needs me right now?" from the top-left quadrant without reading paragraphs. Status words over decorative labels.
2. One screen, one job. The order board never mixes menu editing into scroll; contexts switch by tab, never by surprise.
3. Fail-safe ordering of risk. Accept requires one confident tap; reject requires a reason sheet plus confirmation. Productive actions stay faster than destructive ones by design, not policy memo.
4. Sound carries meaning. Distinct tones map to distinct event families and never reuse the OS default ding that users have learned to ignore.
5. Server truth on timers. Any countdown shown mirrors the backend accept-timer exactly via WebSocket deltas; a lying timer destroys more trust than a missing one.
6. Fatigue-respecting alarms. Rapid identical events coalesce for 30 seconds before re-alerting unless the queue count grows.

## 3. Color system

Same brand skeleton as the customer app; the surface treatment shifts toward high contrast because kitchens glare and staff squint across distance:

| Token | Light | Role | Notes |
| --- | --- | --- | --- |
| color.primary | #2563EB | Brand, selected tab, links | unchanged |
| color.actionAccept | #15803D solid fill | The single green Accept button per card | Deeper than success token specifically so white bold label clears 4.8:1 even on washed screens |
| color.rejectSurface | #FEF2F2 tint with #B91C1C text outline button | Rejection entry only, opens sheet | red as pre-step, never as confirm |
| color.queuePulse | #F59E0B ring on cards awaiting action | Amber means the ball is yours | Amber is reserved exclusively for actionable-now; elsewhere it is banned |
| color.lateAlarm | #DC2626 border 3dp plus tone-C | Deadline inside final third of SLA | distinct two-tone chime family C |
| color.surface / canvas | #FFFFFF / #F1F5F9 | Slightly cooler gray than customer canvas; separates device-from-counter visually | |
| color.textPrimary / Secondary | #0F172A / #334155 | Darker secondary than consumer theme for readability at arm's length | both >= 7:1 |

Dark mode ships day one and defaults ON in store settings: surfaces #0F172A / #101A2C, amber lifts to #FBBF24 for visibility, green accept stays #16A34A with white bold, late border keeps #DC2626 which holds 3.9:1 as a boundary element (border contrast requirement) against dark surfaces.

Status color grammar across the whole app (memorize once, apply everywhere): blue = informational/working, green = done-or-go, amber = yours now, red = error/irreversible/deadline-crisis. No exceptions per screen; violations fail design review.

## 4. Type and touch

Base body size is 16 default like customer, but the order board allows a dense variant at 14 for history lists only. Card titles use Title S 18; prices tabular. The two hero controls — Accept and Start prep — are minimum 56dp tall, full-width inside their card half.

| Style | Spec |
| --- | --- |
| Title L | 22/28 SemiBold screen headers |
| Order number stamp | 20/26 Bold monospaced digits — kitchen callers shout numbers aloud |
| Body / Dense | 16/24 or 14/20 |
| Countdown digits | 22 SemiBold tabular, color follows timer thresholds below |

Touch floors: primary 56dp, secondary 48dp, list rows 64dp so wrist-brushes register on cards not neighbors. Targets in the bottom third of the screen double their visual padding tolerance because one-handed taps under movement land wide.

## 5. Information architecture

Four fixed bottom tabs: Orders board, Menu, Money (payouts plus invoices), More (hours, closures, staff, settings). Nothing hides behind long-press gestures; staff rotate monthly and must rediscover everything by looking.

## 6. Headline flow — incoming order to accepted state

```
0 Idle: device may be face-down or pocketed.
1 FCM high-priority data arrives -> full-screen Alarm layer wakes over
   whatever is open (MOB-RST-04): brand header, order card clone with
   items count + total + delivery zone word, CountdownRing at top-right,
   persistent ring tone family A looping max 45s paired vibration pattern,
   Accept is the ONLY enabled control until opened fully (safety against
   pocket taps) requiring face unlock skip flag per store config.
2 Tap ACCEPT anywhere on the big green panel:
   optimistic UI instantly re-tints card to "Accepted - start when ready"
   with idempotency-key guarded request (MOB-C-04); rollback sheet appears
   only if server rejects (rare), never during happy path.
   Haptic .heavy single thump confirms through noise.
3 Optional detail view: item-level modifier lists expand inline, never new
   screen, preserving the countdown context visually.
Reject path: outlined red button opens ReasonSheet (FR-ORD-03 codes as
tappable chips, free-text optional), then explicit "Confirm reject" button
inside sheet — two deliberate steps separate regret from rashness.
Target instrumented: alarm_sound_start -> accepted_post p50 <= 7 seconds.
```

## 7. Order board states

Board reads top-down strictly by urgency using server-computed buckets:

```
[ ACT NOW ] amber-left-border cards, CountdownRing per card showing
   seconds remaining of accept window (synced via WS delta events;
   if socket lost, chip switches to "reconnecting" gray rather than fake count)
[ IN KITCHEN ] blue-bordered accepted cards advancing PREPARING -> READY
   with fat stage buttons; multi-order lanes capped 6 visible + counter
[ SCHEDULED LATER ], [ HISTORY (searchable) ]
Day stat strip caps at three numbers: new, active, late-today (chunking).
```

Rapid identical updates coalesce per principle 6; queue badges show "+N" growth so attention scales with workload honestly.

## 8. Menu manager and Money screens

Menu manager optimizes for the two edits that actually happen daily: availability flips and price nudges.

- List rows show item thumbnail 56, name, price with inline edit affordance, and a large AvailabilitySwitch (48x84 unique shape so it is unmistakable under motion) writing through immediately with optimistic state plus sync chip if offline.
- Price editing opens a numeric sheet with big keys, shows old vs new on the confirm row, and batches via autosave debounce 1.5s — autonomy reduces edit anxiety while server validation still governs truth.
- Option groups render collapsed under items; adding an option reuses the same numeric sheet.
- Store-health checklist card (missing images, uncovered hours, prep estimate drift) lives at top of Menu tab, one fix per visit philosophy — nudge frequency capped weekly per gap.

Money tab never hides the math: current period gross, commission basis points from contract visible as a line ("Platform fee 12 percent"), net projected, plus historical periods list linking invoice PDFs (FR-PAY-07). Trust here is retention.

## 9. Component specs

| Component | Spec |
| --- | --- |
| OrderCard | left urgency border by bucket color; number stamp monospaced; item summary "3x Kacchi, 2x Borhani"; total Title S; zone word for courier context; countdown ring slot top-right |
| CountdownRing | 56dp ring stroke 5dp; neutral >66 percent remaining, amber 33-66, red <33 with tick-rate increase; disabled gray shows reconnecting state text instead of invented numbers |
| RejectReasonSheet | FR-ORD-03 codes as chips (out of stock, too busy, closing soon, cannot deliver area); chips select-one; confirm button lives inside sheet bottom |
| AvailabilitySwitch | track 84 wide, thumb 40 with icon labels when ON/OFF at edges; writes debounce 500ms |
| StatStrip | exactly three slots max; numbers Bold 20 tabular with overline captions |
| Toast | single global queue; errors retryable inline not via snackbar action chain |

## 10. Sound and haptic grammar

Distinct tone families prevent learned helplessness against notification noise:

| Family | Event | Tone character | Vibration |
| --- | --- | --- | --- |
| A | New order alarm | two-note rising chime loop <=45s | strong triple pulse pattern |
| B | Order reminder pre-timeout (75 percent window elapsed) | single soft double-tick | medium double |
| C | Late/deadline hit | descending urgent pair | long-short-long |
| D | Chat message in thread | subtle pop | none |
| E | Incoming call ring | full 30s ringtone slot reserved distinct from A | continuous until acted |

Volume floor set above media volume stream via audio focus usage permitted for family A while shift toggle is online; families D and E respect user silent-mode except shift-online emergency override documented in store settings.

## 11. Microcopy rules and starter strings

Terse imperative voice, kitchen-compatible: short lines readable at arm's length, no marketing words inside workflows.

| ARB key | en | bn |
| --- | --- | --- |
| acceptNow | Accept order now | অর্ডার এখন গ্রহণ করুন |
| rejectNeedReason | Tell us why to inform the customer | কাস্টমারকে জানাতে কারণ দিন |
| startPrep | Start preparing | প্রস্তুতি শুরু |
| markReady | Food is ready | খাবার প্রস্তুত |
| autoCancelWarn | Auto-cancels in {seconds}s | {seconds} সেকেন্ডে বাতিল হবে |
| payoutLine | Your cut after platform fee | প্ল্যাটফর্ম ফি-র পরে আপনার অংশ |

Keep one script per label; never mix Latin and Bengali characters inside a single word.

## 12. Accessibility in bright kitchens

Minimum contrast maintained against glare assumptions (sunlight or fluorescent); all critical boundaries use 2dp minimum stroke besides color; tone differentiation supports colorblind staff since urgency encodes position + border width + sound, triple-channel; dynamic type up to 1.3 supported on board cards with layout wrapping permitted but hero buttons pinned sizes; TalkBack labels read "Accept order 1047, three items, 620 taka, auto cancel in 4 minutes".

## 13. Psychology playbook

| Effect | Application | Guardrail |
| --- | --- | --- |
| Signal Detection Theory | multimodal alarms (tone family + vibration + color + position) | coalescing prevents alarm fatigue habituation |
| Miller's Chunking | stat strip capped three numbers; lanes capped six | overflow counters honest "+N" |
| Idempotent safety | double-tap protected client-side via MOB-C-04 key reuse | rollback sheets rare, calm copy |
| Loss framing avoided on reject | reason sheet informs customer, never shames staff | reasons map FR-ORD-03 codes only |
| Progress principle | Money tab delta "today vs yesterday same weekday" | real aggregates only |
| Muscle memory placement | Accept always bottom-right of its card region across layouts | layout shifts prohibited during active alarms |

## 14. UX instrumentation

alarm_sound_start_ms, accepted_post_ms derived difference feeding p50 target <=7s; sla_breach_rate per branch paired against prep_p90 analytics column; reject_reason_distribution; availability_flip_to_order_missed correlation query ticket for ops; menu_edit_sessions per week; payout_view_frequency as trust pulse.

## 15. Developer handoff checklist

Alarm layer uses FCM high-priority data plus local-notification fallback verified killed-app on both platforms (Android exact-alarm permission decision recorded); CountdownRing subscribes WS deltas and displays reconnecting truthfully on socket loss; idempotency intercept wired globally per MOB-C-04; tone families bundled within flavor assets respecting size budget; dense variant typography token shipped; traceability mapped to MOB-RST-01..10 in PROJECT_PLAN section 8.4; both themes screenshot-archived under fluorescent-light emulation filter.