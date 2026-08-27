# Customer App — UI Design Instructions

| Field | Value |
| --- | --- |
| Document | docs/design/CUSTOMER_APP_UI.md |
| Version | 1.0 |
| Date | 2026-08-27 |
| Owner | Design lead |
| Related | PROJECT_PLAN.md sections 8.3 and 10, ARCHITECTURE.md sections 9-11, tokens owned by `packages/core_ui` |

---

## 1. Who we are designing for

The customer opens this app with a biological clock ticking: hunger lowers patience, raises irritation at small frictions, and amplifies distrust of anything unclear about money. Sessions are short (median under 3 minutes for reorders), one-handed, often on cellular, sometimes walking.

| Persona snapshot | Context | Emotional driver | Design answer |
| --- | --- | --- | --- |
| Commuter, lunch break | One hand, 45-70 minutes window | Fear of being late back to work | Time-to-doorway estimate above the fold; reorder in 3 taps |
| Family planner, evening | Two hands, couch, compares options | Wants confidence in value and quality | Transparent totals, rating evidence, no surprise fees ever |
| First-time explorer | Distrustful, price-sensitive, gift/splurge occasions | Fear of being cheated or waiting forever | Fee breakdown always visible pre-checkout; money-back promises only where operations truly guarantees them |

Core insight: in food apps the product is not the food photo, it is the promise of a predictable arrival time. Every screen either strengthens or erodes that promise.

## 2. Experience principles

1. Default forward. The next-best action is preselected (default address, default payment method, recommended item) so a hungry brain approves rather than constructs. Rationale: Hick's Law — decision cost grows with options presented.
2. Never hide a charge. Fees render as an always-open breakdown line before any payment step. Surprise costs discovered late are the number one abandon trigger and a trust scar that outlives the session.
3. Progress is a feature. From "added to cart" to "courier is downstairs", every wait displays position and remaining steps. Perceived control reduces perceived waiting more than actual seconds saved.
4. Honest scarcity only. Reservation timers reflect real quote TTLs served by the pricing engine; nothing ticks artificially. Fake urgency trains users to ignore the interface.
5. Calm by default. Motion affirms actions; red exists solely for errors and genuine deadlines. If everything shouts, nothing is heard.
6. Reversible feels safe. Destructive intents (cancel order, clear cart) get friction; productive intents get none.

## 3. Color system

Brand core Plate Blue carries identity and informational states. Conversion accent Flame Orange is deliberately rationed: one orange element visible per viewport maximum.

| Token | Light | Role | Psychology | Contrast rule |
| --- | --- | --- | --- | --- |
| color.primary | #2563EB | Trust anchor, links, tracking header, selected tab | Blue reads competent and secure in commerce | On white 4.54:1 body-safe |
| color.accent | #EA580C | Primary CTAs (Add to cart, Checkout, Apply), deal badges | Warm hue stimulates appetite and urgency without alarm tone | White label only at >= 16sp semi-bold; below that switch to color.accentStrong |
| color.accentStrong | #C2410C | Accent on small text, pressed state | Same warmth, heavier weight perception | With white 5.4:1 body-safe |
| color.success | #16A34A | Confirmation moments, order accepted, funds applied | Completion relief | Pair with icon, never color alone |
| color.warning | #D97706 | Quote expiring soon banner | Soft urgency ahead of hard deadline | Text uses warningDeep #92400E on tinted bg |
| color.danger | #DC2626 | Errors, cancellations, destructive only | Reserve scarcity keeps its power | Body-danger uses dangerDeep #B91C1C |
| color.textPrimary | #0F172A | Headlines, prices | Highest authority ink | 16.9:1 |
| color.textSecondary | #475569 | Supporting lines | Recedes politely | 7.4:1 |
| color.border | #E2E8F0 | Card outlines, dividers | Borders beat shadows for calm scanability | Decorative, exempt |
| color.surface | #FFFFFF | Cards | | |
| color.canvas | #F8FAFC | Screen background | Elevates white cards softly | |

Dark theme mapping: canvas #0B1220, surface #121B2E, border #263349, textPrimary #EDF2FA, textSecondary #9AA8BD, primary lifted to #60A5FA for text/icon roles only (buttons stay solid #2563EB with white label), accent stays #EA580C background with white bold label, success #22C55E, danger #F87171 reserved for icons/text pairs on dark. Both themes ship day one; follow OS setting, offer manual override under profile.

Forbidden pairings: orange backgrounds behind red text, two accents competing in one card, status colors decorating non-status content (colored for decoration teaches users to ignore color as meaning).

## 4. Type, spacing, touch

Type ramp (Inter bundled; Noto Sans Bengali auto-substitutes for bn locale):

| Style | Spec | Usage |
| --- | --- | --- |
| Display | 30/38 Bold -0.5 | Order success moment only |
| Title L | 22/28 SemiBold | Screen headers |
| Title S | 18/24 SemiBold | Card titles, prices |
| Body | 16/24 Regular | Default |
| Body S | 14/20 | Secondary lines |
| Caption | 12/16 Medium | Meta labels; never for actions |
| Overline | 11/12 Medium caps +4% tracking | Section eyebrows |

Prices always render in Title S or larger with tabular figures; never Caption — money is content, not decoration.

Spacing on an 8pt grid (half-steps 4): screen gutters 16, card padding 16, inter-card 12, intra-group 8. Radii: card 16, sheet 20 top-only, input 12, chip pill. Elevation is banned in favor of 1px borders plus canvas contrast — flat cards scan faster and behave predictably under both themes.

Touch: minimum target 48x48 with 8px spacing between adjacent targets; the persistent cart bar is 56 tall; all bottom sheets include a 24px grab handle. Thumb-zone rule: anything needed mid-scroll (add button, quantity stepper) lives in the right-hand lower quadrant of its card, reachable while the thumb rests.

## 5. Information architecture

Bottom navigation, exactly three tabs — Home, Orders, Profile — because a cart destination does not need a tab when a persistent cart bar exists.

```
[ Home ]      discovery rails, search entry, vouchers entry
[ Orders ]    active tracker pinned atop history list
[ Profile ]   addresses, payments methods list, security center,
              preferences, help threads
+ Persistent CartBar (56dp) floats above nav whenever cart > empty:
    [n items] [running total] [View cart ->]
```

The CartBar is the single most important stateful widget in the app: it must never jump layout, must animate value changes by count-up tween (300ms), and deep-links back into cart preserving scroll position. Seeing accumulated value persistently exploits endowed-progress without any dark pattern.

## 6. Headline flows

Flow A — first order, browse to placed order in under 90 seconds:

```
1 Home (location bar visible, default address preloaded)
2 Search or rail tap -> results grid filtered open-now by default
3 Restaurant page -> item tile [+] adds DEFAULT options instantly
   (customization optional via long label tap; Hick's Law satisfied)
4 CartBar -> Cart (breakdown ALWAYS expanded, voucher field inline)
5 Checkout -> address confirmed as default, payment method preselected
   (Stripe sheet tokenized before place runs), total matches quote TTL
6 Place -> Success moment: Display style check-in-circle micro-anim
   + haptic .medium, honest line "Sabbir at Chillox accepted in 2m" replaced
   later by live tracking push
Psychology annotations: steps 3 and 5 contain zero required decisions;
the quote-expiry pill uses warning color ONLY under 2 minutes remaining.
```

Flow B — live tracking screen (the emotional core):

```
Layout zones top->bottom: sticky status header (plain-language stage line),
map (~55% viewport) with courier marker and route polyline, timeline strip
(Placed - Accepted - Picked - Delivered) where completed nodes fill blue,
contextual action row (Chat thread icon, Call icon shown per FR windows),
bottom sheet collapsing to one-line ETA that expands on drag.
Anxiety rules: ETA text renders "Arrives by 7:42 PM" absolute time, updates
never flicker more often than 15s, delays switch header to plain explanation
plus support shortcut instead of red alarm styling. The map renders OSM tiles
per ARCHITECTURE section 9 behind a MapPane abstraction.
Peak-end rule application: the delivered state shows order photo prompt ONLY
after showing thanks; rating is requested post-meal via push, not ambushed.

## 7. Remaining screens (condensed instructions)

| Screen | Primary question it answers | Non-negotiables |
| --- | --- | --- |
| Search results | "What is available near me right now?" | open-now filter on by default; skeletons for first paint; zero-results offers cuisine pivots instead of dead end |
| Restaurant page | "Can I trust this place and find my dish fast?" | Sticky trust strip (rating count from real aggregates, prep time); category chips scroll-synced to list; availability gray-out with reason |
| Cart | "What am I paying in total?" | breakdown expanded; voucher inline with instant validation message; quantity steppers within thumb zone; reservation pill honest TTL |
| Vouchers page | "What can I actually use?" | applicable-vs-expired separated; T&C via expandable, never modal wall |
| Address manager | "Where are we delivering?" | map-pin placement first-class; default star toggle; single-default partial rule respected visually |
| Review composer | "Worth recommending?" | inline star range errors; soft counter appears after 800 chars of 1000 cap |
| Security center | "Am I safe here?" | sessions view clarity; OTP reset entry reusing branded flow; deletion path per FR-AUTH-09 |
| Notifications center | "Did I miss anything?" | grouped by day; unread dot only; preferences deep link |

Every screen defines its empty state as an action ("No orders yet — Home is two taps away") rather than an apology.

## 8. Component specs

| Component | Spec highlights |
| --- | --- |
| Button.primary | bg color.accent, radius 12, height 48/56 prominent, label white SemiBold >=16sp else switch bg to accentStrong; pressed darkens 8 percent; success auto-dismiss 1.2s |
| RestaurantTile | image 96 square left, title Title S, rating chip plate-blue outline with star glyph, eta Caption, at most one orange deal ribbon |
| QuoteExpiryPill | neutral by default; warning tint under 120 seconds with a single gentle pulse; hard expiry swaps cart CTA into Refresh quote |
| BreakdownRow | label Body S secondary, value Title S tabular figures; savings rows show new total in success beside struck-through original |
| TimelineStrip | four nodes on 6dp track; active node opacity pulse 0.4 to 1 at 1.2s period; completed nodes fill primary |
| SkeletonLoaders | mirror final geometry exactly, shimmer 1s linear low contrast, swap atomically on data arrival |

## 9. Motion and haptics

Durations: micro 120ms for chips and ripples; standard 240ms for sheets and card entrances; celebratory 600ms maximum once per session (success check only). Easing emphasized cubic(0.2,0,0,1) entering, decelerate exiting. Haptics: light tick on add-to-cart, medium confirm on order placed, silence elsewhere except system alerts. Every interactive element acknowledges within 100ms visually — the Doherty threshold applied to touch, not just network speed.

## 10. Microcopy rules and starter strings

Voice: warm, concrete, never groveling. Errors state what happened plus the single next step. Banned: oops, whoops, stacked exclamation marks, apology chains without action.

| ARB key | en | bn |
| --- | --- | --- |
| addToCart | Add to cart | কার্টে যোগ করুন |
| feeBreakdownTitle | Your total, fully shown | সম্পূর্ণ হিসাব দেখুন |
| quoteExpiring | Items reserved: {minutes} min | আইটেম সংরক্ষিত: {minutes} মিনিট |
| courierOnWay | {name} picked up your order | {name} আপনার অর্ডার নিয়ে রওনা হয়েছে |
| etaLine | Arrives by {time} | {time} এর মধ্যে পৌঁছাবে |
| threadClosedHint | This conversation closed after delivery | ডেলিভারির পরে কথোপকথন বন্ধ |
| genericError | That did not go through. Retry? | কাজ হয়নি। আবার চেষ্টা করবেন? |

Bengali copy expands roughly 15 percent versus English; layouts must absorb +30 percent before any ellipsis truncation is allowed.

## 11. Accessibility checklist (release gate)

Dynamic type honored to 1.3x with no clipped CTAs; body pairs meet 4.5:1 and large-text pairs 3:1 verified against the token table; TalkBack/VoiceOver reads each headline flow in visual order using content labels ("Add Kacchi Biryani to cart, 320 taka", never bare "button"); focus order matches reading order; reduce-motion replaces celebratory animation with a static scale-in; no gesture-only affordances anywhere.

## 12. Psychology playbook

| Effect | Where used | Guardrail against dark pattern |
| --- | --- | --- |
| Hick's Law | default options, three tabs, curated rails | customization stays one tap deeper, not hidden |
| Goal-Gradient | CartBar running total, tracker timeline fill | progress reflects server truth only |
| Peak-End Rule | success moment, post-delivery thanks first | celebration never gates the next step |
| Loss Aversion | reservation TTL pill | timer mirrors pricing engine TTL exactly (FR-CART-05) |
| Social Proof | rating chip, popularity tag | aggregates only from FR-RVW-03, never invented badges |
| Anchoring | struck-through original beside discounted total | original price must have genuinely applied |
| Endowed Progress | persistent CartBar retaining value across sessions | clearing requires explicit user action |
| Doherty Threshold | sub-100ms touch acks, skeleton-to-content swaps | loading states specified per screen |

## 13. UX instrumentation

Events feed analytics rollups so design claims stay measurable rather than aesthetic opinions:

checkout_step_view, checkout_step_abandon{step}, add_to_cart{source=rail|search|pdp}, reorder_tap_count distribution, track_open_rate, eta_accuracy_delta_seconds computed against delivered_at, review_prompt_shown/submitted, fee_breakdown_expand as a trust-health curiosity signal, voucher_apply_success_rate.

Post-launch baselines after 500 sessions: reorder path median under 60 seconds, checkout completion above 82 percent, tracker opens between 3 and 8 per order — a lower bound signals push decay, an upper bound signals unresolved anxiety in copy or ETA truthfulness.

## 14. Developer handoff checklist

Design tokens published from `packages/core_ui` consuming the JSON contract in both themes; MapPane abstraction wired per ARCHITECTURE section 9 (OSM tiles behind config); skeleton screens implemented for every network-backed surface listed in section 7; ARB files updated with section 10 keys and native-reviewed Bengali; dynamic-type screenshot archive at 1.0x and 1.3x for both locales; accessibility script executed before merge; traceability complete when every screen maps to MOB-USR-01..12 in PROJECT_PLAN section 8.3.