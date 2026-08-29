# PrivatPirat One-Tap Prototype v0.1 — functional checkpoint

**Checkpoint:** 2026-08-29 05:05 +03:00  
**Scope:** PP-LAB-01 / Happ one-tap subscription import prototype  
**Verdict:** `FUNCTIONAL PASS / BOOTSTRAP TRANSPORT NOT ACCEPTED FOR PRODUCTION`

## Goal

Prove the user flow:

`one link -> Happ -> one subscription -> PP-LAB-I + PP-LAB-II + PP-LAB-III`

without publishing working server IPs, client URIs, UUIDs, REALITY material, Hysteria credentials, certificate pins, subscription tokens or raw client configuration.

## Facts

- `FACT` — a sanitized local subscription bundle containing exactly two VLESS profiles and one Hysteria2 profile was assembled from the already accepted PP-LAB-I / II / III client material.
- `FACT` — Happ supports the three target profiles in one subscription; the prototype successfully created one subscription containing Privat Pirat I, Privat Pirat II and Privat Pirat III.
- `FACT` — the Happ deep-link flow was proven to work when the subscription endpoint was reachable.
- `FACT` — PP-LAB-I, PP-LAB-II and PP-LAB-III remained active and unchanged throughout the accepted one-tap experiment.
- `FACT` — the delivery origin was bound only to localhost and protected by a high-entropy secret path; an invalid path returned 404.
- `FACT` — external HTTPS delivery through a Cloudflare Quick Tunnel succeeded over HTTP/2 and returned exactly `2 VLESS + 1 Hysteria2`.
- `FACT` — the working subscription URL and all three working client URIs remained outside GitHub, chat and Google Drive.
- `FACT` — direct Happ refresh/import through the temporary `trycloudflare.com` endpoint was unreliable when the phone had no already-working VPN path; with VPN enabled, the same subscription imported and expanded correctly.

## Security decision

A public IP certificate for PP-LAB-01 was rejected for this delivery prototype because it would make the origin IP publicly discoverable through Certificate Transparency. The experiment therefore used a separate outbound tunnel for bootstrap delivery.

The temporary Cloudflare Quick Tunnel is accepted only as a laboratory transport. It is **not** accepted as the production bootstrap layer because a new customer must be able to obtain the VPN configuration before any VPN is already active.

## Harness lessons

- Expected polling misses such as `grep` returning no match while waiting must never terminate a script under `set -e` / `pipefail`.
- A connectivity probe must not be treated as authoritative when it does not reproduce the real client's TLS behavior.
- PASS must never be printed after an upstream failure.
- Rollback must remove only the current experimental delivery components and preserve the accepted VPN routes.
- A client bootstrap path must be tested from the exact initial state expected for a new user: no pre-existing PrivatPirat/VPN dependency.

## Product acceptance result

The core product interaction is proven:

`one subscription link -> Happ -> one subscription -> I + II + III`

Therefore `PrivatPirat One-Tap Prototype v0.1` receives a **functional PASS**.

The bootstrap transport receives **FAIL for production suitability** because it is not reliably reachable from the target direct-connectivity state without an already active VPN.

## Next stage

`PrivatPirat Bootstrap Gateway v0.1`

Acceptance target:

- reachable from the target Russian network without a pre-existing VPN;
- ordinary trusted HTTPS transport;
- origin VPN node is not exposed through public DNS/certificate metadata;
- one private link imports exactly I + II + III into Happ;
- no operational secrets in GitHub/chat/Drive;
- independent rollback and lifecycle from PP-LAB-I / II / III.
