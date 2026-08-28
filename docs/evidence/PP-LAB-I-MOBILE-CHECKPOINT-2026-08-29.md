# PP-LAB-I — mobile recovery checkpoint

**Evidence ID:** `PP-LAB-I-MOBILE-CHECKPOINT-2026-08-29`

**Local checkpoint time:** 2026-08-29 00:23 (UTC+3)

**Route:** `PP-LAB-I` — VLESS RAW/TCP REALITY/Vision

**Verdict:** `PARTIAL` — mobile client acceptance is confirmed; server restart recovery and stop/start isolation remain open.

## Confirmed facts

- Android mobile regression was resolved with one minimal client-side change: uTLS fingerprint `chrome -> firefox`.
- No VPS, Xray, firewall, route port, credential, REALITY key material, SNI/target, or other server-side setting was changed to obtain the recovery.
- Real application traffic was confirmed after the fix; acceptance was not based only on a client `connected` indicator.
- Termux was explicitly included in the Android per-app proxy/VPN selection and a subsequent exit-path check confirmed that Termux traffic used `PP-LAB-I`.
- Mobile client validation produced three successful clean reconnect validations. Each successful validation included DNS resolution, HTTP body transfer, HTTPS body transfer, and two independent exit-IP checks matching the expected server exit.
- One intermediate reconnect attempt produced a transient exit-IP check failure while DNS/HTTP/HTTPS still passed. A distinguishing read-only check immediately afterward used three independent exit-IP endpoints and all three matched; a subsequent clean reconnect then passed the full client suite.
- A dedicated passphrase-protected ED25519 SSH identity was created on the POCO/Termux endpoint for PP-LAB-01 administration.
- The dedicated mobile public key was added to the server through an authenticated root session; key-only login was then verified with `MOBILE_SSH_KEY=PASS`.
- Read-only systemd inventory from the mobile SSH path found `xray.service` active/running and enabled. The template `xray@.service` exists but is not the active route unit at this checkpoint.

## Security boundary

This public evidence intentionally omits the server address, port, UUID, REALITY values, SNI/target, SSH fingerprints, private/public operational key material, passwords, connection URIs, and raw configuration.

The working client backup and SSH private key remain outside the public repository.

## Remaining G2 work

1. Confirm structurally, without exposing secrets, that the active `xray.service` is the PP-LAB-I service being accepted.
2. Perform server-unit restart recovery and repeat the client data-path check.
3. Perform route stop/start isolation and verify expected loss/recovery of PP-LAB-I without unintended impact.
4. If all required checks pass, record final sanitized evidence and change `G2` from `PARTIAL` to `PASS`.
