# PP-LAB-01 — four-friend recipient checkpoint

**Checkpoint:** 2026-09-13  
**Scope:** additive recipient layer on the accepted primary `PP-LAB-01` node  
**Verdict:** `RECIPIENT LAYER PASS / LANDING UX DEFERRED`

## Facts

- `FACT` — the accepted `PP-LAB-I`, `PP-LAB-II` and `PP-LAB-III` baseline remained the existing three-route runtime; this checkpoint did not add a fourth route or redesign route selection.
- `FACT` — four independent private recipient identities were added alongside the existing owner identity; the owner identity was preserved rather than reissued.
- `FACT` — each recipient receives its own three-route subscription identity; working credentials, tokens and subscription URLs remain private and are not recorded here.
- `FACT` — the recipient change was performed with a new private backup namespace and did not overwrite the legacy rollback material.
- `FACT` — the existing Cloudflare Named Tunnel configuration, DNS/firewall scope and external hostname were not changed by the recipient-layer transaction.
- `FACT` — the final client-side result was confirmed in Happ: the subscription header is `DeepWork AILab` and the three route labels are `🇺🇸 Privat 🏴‍☠️ Pirat I`, `🇺🇸 Privat 🏴‍☠️ Pirat II` and `🇺🇸 Privat 🏴‍☠️ Pirat III`.
- `FACT` — the recipient layer uses the already accepted persistent subscription transport; this checkpoint is not a new G2/G3/G4 acceptance and does not replace the earlier route evidence.

## Decisions

- `DECISION` — direct Happ subscription links are the current distribution path for the four friends.
- `DECISION` — an active/clickable Landing-based delivery flow is explicitly postponed to a later, separate gate.
- `DECISION` — the deferred Landing work is not a blocker for the current four-recipient result.
- `DECISION` — future Landing work must preserve the current owner identity, the four recipient identities, the accepted I/II/III routes and the existing rollback boundary unless a later explicit gate authorizes otherwise.

## Deferred work

- `TODO` — design and verify the active-link Landing UX in a separate gate.
- `TODO` — when that gate is opened, verify zero-state use with VPN off, exact recipient-to-subscription mapping and regression of the current direct Happ path before accepting the Landing change.

## Security boundary

This record intentionally excludes working server/SSH metadata, hostname, subscription paths, recipient tokens, UUIDs, REALITY material, Hysteria credentials, certificate material, SNI, complete client/server configs and working URIs.
