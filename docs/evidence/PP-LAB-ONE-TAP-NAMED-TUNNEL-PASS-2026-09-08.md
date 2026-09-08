# PrivatPirat One-Tap — Cloudflare Named Tunnel checkpoint

**Checkpoint:** 2026-09-08  
**Scope:** persistent One-Tap delivery transport and zero-state Happ acceptance  
**Verdict:** `NAMED TUNNEL DELIVERY + REBOOT PERSISTENCE PASS`

## Facts

- `FACT` — the previously accepted PP-LAB-I, PP-LAB-II and PP-LAB-III routes were not changed during this checkpoint.
- `FACT` — the delivery origin was proved again to be loopback-only.
- `FACT` — a Cloudflare Named Tunnel was created and its connector reached healthy state.
- `FACT` — the temporary Quick Tunnel runtime was replaced by the Cloudflare Named Tunnel.
- `FACT` — a stable custom-domain HTTPS hostname was routed to the loopback-only delivery origin.
- `FACT` — the real private subscription endpoint returned HTTP success through the stable HTTPS route.
- `FACT` — the delivered subscription passed the composition check with exactly 2 VLESS + 1 Hysteria2.
- `FACT` — the local One-Tap artifacts on Android were migrated from the old temporary hostname to the stable hostname while preserving the private high-entropy subscription path.
- `FACT` — Happ imported one new subscription containing PP-LAB-I, PP-LAB-II and PP-LAB-III.
- `FACT` — with the existing VPN switched off, Happ successfully refreshed the new subscription.
- `FACT` — after the zero-state refresh, PP-LAB-I, PP-LAB-II and PP-LAB-III remained present and a working route connected successfully. This connection observation is part of the One-Tap acceptance and is not presented as a new full data-path acceptance for the routes.
- `FACT` — a controlled VPS reboot was actually observed, and the boot identity changed, proving that a new boot occurred.
- `FACT` — the PP-LAB-I, PP-LAB-II and PP-LAB-III route runtimes returned automatically after reboot.
- `FACT` — the loopback delivery service returned automatically after reboot.
- `FACT` — the Named Tunnel connector service returned automatically after reboot.
- `FACT` — the stable public HTTPS subscription endpoint remained reachable after reboot.
- `FACT` — the post-reboot subscription composition remained exactly 2 VLESS + 1 Hysteria2.
- `FACT` — with the pre-existing VPN switched off after reboot, Happ successfully refreshed the persistent subscription.
- `FACT` — after this zero-state post-reboot refresh, PP-LAB-I, PP-LAB-II and PP-LAB-III remained present and the user confirmed successful operation. These observations verify persistence and bootstrap behavior; they are not a new full G2, G3 or G4 route acceptance.
- `FACT` — rollback for the server-side Named Tunnel switch was prepared.
- `FACT` — no client credentials or subscription secret are included in this public evidence.

## Decisions

- `DECISION` — Cloudflare Named Tunnel with a stable custom-domain HTTPS hostname is the currently accepted One-Tap bootstrap transport for this checkpoint.
- `DECISION` — the current Named Tunnel One-Tap transport is accepted as reboot-persistent for this checkpoint.
- `DECISION` — Quick Tunnel is no longer the current One-Tap bootstrap transport.

## Remaining gates

- `TODO` — the per-user subscription and credential layer remains a separate next product gate.
- `TODO` — the prior decision to use a separate Bootstrap Gateway is not changed automatically; whether it is still needed will be reviewed separately.

## Public evidence boundary

This record intentionally contains no public hostname or domain, tunnel name or credential, server address or SSH metadata, exact loopback port, private subscription path or complete URL, UUID, REALITY or Hysteria credentials, Short ID or SNI, client URI, raw configuration or log, or password-manager data.
