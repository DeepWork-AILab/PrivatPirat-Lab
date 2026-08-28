# PP-LAB-I — G2 final acceptance

**Evidence ID:** `PP-LAB-I-G2-PASS-2026-08-29`

**Local acceptance time:** 2026-08-29 00:35 (UTC+3)

**Route:** `PP-LAB-I` — VLESS RAW/TCP REALITY/Vision

**Verdict:** `PASS`

## Acceptance summary

- Wi-Fi data path: PASS with three clean reconnect repetitions.
- Independent browser DNS leak assessment: PASS for the accepted Wi-Fi checkpoint.
- Android mobile regression: resolved by the minimal client-side change `fingerprint: chrome -> firefox`.
- Android mobile data path after the fix: PASS.
- Mobile clean reconnect acceptance: PASS. Successful validations included DNS resolution, HTTP transfer with a non-empty body, HTTPS transfer with a non-empty body, and independent exit-IP agreement with the expected server exit.
- A transient exit-IP check during one intermediate reconnect was investigated with a distinguishing read-only test; three independent exit-IP endpoints then agreed, and a subsequent clean reconnect passed the full client suite.
- Mobile administration path: PASS. A dedicated passphrase-protected ED25519 SSH identity on POCO/Termux was authorized on PP-LAB-01 and key-only login was verified.
- Active route unit identification: PASS. Read-only systemd/config-structure inspection confirmed that the active `xray.service` serves a VLESS / RAW / REALITY / Vision inbound matching PP-LAB-I without exposing operational secret values.
- Server-unit restart recovery: PASS. The Xray service was restarted, its process instance changed, the unit returned to `active`, and the full client data path returned with DNS/HTTP/HTTPS and two exit-IP checks passing.
- Stop/start isolation and recovery: PASS. Stopping the PP-LAB-I Xray unit caused the route to become unavailable as expected. An independently scheduled server-side recovery started the unit again; the route returned, the service was `active`, and DNS/HTTP/HTTPS plus two exit-IP checks all passed.

## Security boundary

This public evidence omits operational server addresses, route ports, UUIDs, REALITY values, SNI/target, SSH fingerprints, private/public operational key material, passwords, connection URIs, full client configurations, and raw logs.

The working client backup and SSH private key remain outside the public repository.

## Gate result

`G2 — PP-LAB-I: PASS`

This unblocks `Stage 3 / G3 — PP-LAB-II` under the existing experiment protocol. PP-LAB-I must remain unchanged while PP-LAB-II is built, and PP-LAB-I must pass the required regression checks before PP-LAB-II can be accepted.
