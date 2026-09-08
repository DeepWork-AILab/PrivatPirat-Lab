# PrivatPirat One-Tap — Cloudflare Named Tunnel checkpoint

**Checkpoint:** 2026-09-08  
**Scope:** persistent One-Tap delivery transport and zero-state Happ acceptance  
**Verdict:** `NAMED TUNNEL DELIVERY PASS / VPS REBOOT PERSISTENCE NOT YET PROVEN`

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
- `FACT` — rollback for the server-side Named Tunnel switch was prepared.
- `FACT` — no client credentials or subscription secret are included in this public evidence.

## Decisions

- `DECISION` — Cloudflare Named Tunnel with a stable custom-domain HTTPS hostname is the currently accepted One-Tap bootstrap transport for this checkpoint.
- `DECISION` — Quick Tunnel is no longer the current One-Tap bootstrap transport.

## Remaining gates

- `TODO` — real VPS reboot persistence of the Named Tunnel is not yet proven and remains a separate gate.
- `TODO` — the per-user subscription and credential layer remains a separate next product gate.
- `TODO` — the prior decision to use a separate Bootstrap Gateway is not changed automatically; its relevance will be reviewed separately after reboot acceptance.

## Public evidence boundary

This record intentionally contains no public hostname or domain, tunnel name or credential, server address or SSH metadata, exact loopback port, private subscription path or complete URL, UUID, REALITY or Hysteria credentials, Short ID or SNI, client URI, raw configuration or log, or password-manager data.
