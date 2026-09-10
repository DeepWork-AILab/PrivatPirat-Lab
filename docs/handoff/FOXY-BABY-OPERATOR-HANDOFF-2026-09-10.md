# Foxy Baby — operator handoff

**Checkpoint date:** 2026-09-10  
**Project:** PrivatPirat Lab  
**Status:** ready to continue in a new project chat  
**Canonical source:** `DeepWork-AILab/PrivatPirat-Lab`, branch `main`

## Purpose

This handoff captures the current Foxy Baby state after a long recipient-delivery and bootstrap session so a new chat can continue without reconstructing history from memory.

Before new work, read `AGENTS.md`, `README.md`, `docs/EXPERIMENT_PROTOCOL.md`, `docs/evidence/FOXY-BABY-HARDENING-POST-REBOOT-2026-09-04.md`, `docs/evidence/FOXY-BABY-RECIPIENT-DELIVERY-CHECKPOINT-2026-09-10.md`, and `docs/evidence/PP-LAB-ONE-TAP-NAMED-TUNNEL-PASS-2026-09-08.md` when comparing the working primary One-Tap pattern.

GitHub `main` wins over older chat or Drive notes when they conflict.

## Security boundary

This public handoff intentionally omits working hostnames, addresses, ports, tunnel identifiers, SSH metadata, recipient names, UUIDs, REALITY material, Hysteria credentials, tokens, complete working links, SNI and raw configurations.

Private operator state remains on the server and in owner-local material. A future assistant must retrieve current private values only through read-only local/operator access and must not paste them into GitHub or chat.

## Route and acceptance state

Foxy Baby has three independent routes: VLESS/TCP/REALITY, VLESS/XHTTP/REALITY and Hysteria2/TLS/QUIC.

Key-only administration, default-drop firewall persistence and route reboot recovery are established. The private Android/mobile route matrix has passed, but the complete formal Wi-Fi matrix remains pending. Do not label Foxy Baby as a second formal G2/G3/G4 node until the missing target-network acceptance is completed.

## Authentication model

Current structure is one owner-only identity plus three independent recipient identities. Each recipient has separate authentication across the three routes and its own subscription identity.

Independent revoke/rotation was proven for one recipient without affecting the other two. The old shared operator credentials were revoked after the replacement owner-only credentials were validated.

Do not recreate recipients or restore old shared credentials without a new explicit gate.

## Operator shortcut: regenerate the three current Happ delivery keys

In a future chat the owner may simply ask:

> «Дай одну команду в Termux, которая выведет три текущих Foxy Baby Happ-ключа».

Expected assistant behavior:

- use the already configured Foxy SSH alias rather than asking the owner to retype host data;
- perform a read-only lookup of the existing root-only recipient catalog with passwordless sudo;
- resolve exactly the current three recipient subscription identities and the current accepted stable subscription endpoint from private runtime/operator state;
- locally compose the three Happ add keys and print them only in the owner's Termux session with human-readable labels;
- never copy resulting keys, tokens or complete working links into ChatGPT, GitHub, Drive, issues or evidence;
- never mistake a bare subscription token for a usable client import key;
- if the manifest structure or current stable endpoint cannot be proven read-only, STOP instead of guessing.

The exact command and private paths are intentionally not stored in this public handoff. They should be reconstructed from current private server state at execution time.

## Persistent delivery state

Accepted delivery uses one stable Cloudflare Named Tunnel with separate loopback-only persistent origins for the personal landing and subscription delivery.

The stable subscription endpoint passed all three recipient checks, canonical/live exact matching, expected three-profile composition and unknown-token handling. The persistent origins and Named Tunnel connector returned automatically after a controlled reboot.

Temporary Quick Tunnel delivery is legacy history, not the accepted persistent transport.

## Happ UX observations

Direct stable Happ keys work and expand into the intended three-profile subscription.

Observed client variability included a technical-hostname title before refresh and a misleading timeout notification even when the subscription had already been added. Later repeated direct-key imports also completed cleanly. Treat this as client UX variability unless independent evidence shows a route or subscription data-path failure.

## Personal Landing facts

Read-only audit established that the landing token is kept in the URL fragment on initial load, then posted same-origin to resolve the recipient subscription, and the visible button invokes Happ with the resolved stable subscription.

No evidence supports replacing this with an invented import URI form. Do not redesign Landing or VPN infrastructure without a concrete failing boundary.

## Remaining zero-state issue

Target user flow is ordinary mobile data with VPN off: open the personal HTTPS Landing, launch Happ, obtain the recipient subscription and then connect.

Current evidence on one Android mobile-data path:

- with another VPN already active, Landing/Happ works;
- with VPN off, two browsers showed an effectively blank Landing page;
- an autonomous VPN-off probe reached HTTPS and received HTTP 200/text-html but zero body bytes before timeout;
- a forced HTTP/1.1 request began receiving response-body bytes;
- a forced HTTP/2 request received 200 headers and then stalled at zero body bytes until timeout;
- the HTTP/1.1 run itself ended early because its local Termux output path did not exist, so it is not a complete HTTP/1.1 acceptance;
- a direct loopback probe of the Foxy Landing origin returned the complete declared body with matching Content-Length and no transfer/content-encoding anomaly;
- a read-only Cloudflare comparison found no explanatory difference in tunnel health, proxied DNS path, Access, Workers, custom WAF, redirect, transform, cache/configuration or origin rules versus the working primary One-Tap pattern.

Current hypothesis: HTTP/2 behavior on the VPN-off mobile client-to-edge path is the leading discriminator, but carrier path versus edge behavior versus another transport interaction remains unproven.

## Response-body-buffering experiment status

A narrow Cloudflare experiment was proposed for only the Landing path: disable response-body buffering while leaving DNS, tunnel, zone-wide HTTP settings, TLS, WAF, Workers, cache, subscription delivery and all three VPN routes unchanged.

Two Browser Assistant attempts stopped before the setting-availability check because Cloudflare dashboard navigation/Chrome control timed out. Both attempts ended with `WRITE_PERFORMED=NO`.

The night session ended before any manual UI change was made. Therefore this experiment is **NOT APPLIED**. A future attempt requires a fresh gate and a full impact/expected/verification/backup/rollback/stop statement.

## Controlled reboot result

A real controlled reboot proved return of all three route units, both persistent origins and the Named Tunnel connector. Stable Landing and all three subscription endpoints returned, canonical/live matching and expected composition remained intact, unknown-token handling remained correct and failed systemd units were zero.

Do not rerun the reboot merely to prove the same persistence again unless a relevant configuration changes.

## What not to redo

Absent concrete new evidence, do not redo recipient provisioning, shared-access cutover, revoke/rotation proof, persistent connector deployment, persistent-origin migration, subscription-handler correction, stable HTTPS three-recipient acceptance, controlled reboot persistence or the already completed Android/mobile route matrix.

The missing formal target-network work is Wi-Fi, not another blind mobile rerun.

## Legacy cleanup boundary

Old transient delivery artifacts and an invalid historical nested subscription hostname may remain as rollback/legacy remnants. Do not remove them opportunistically. Cleanup is a separate R3 gate after proving they are no longer required for rollback or recovery.

## Commercial relevance

The Landing is not the core commercial skill. The sellable capability is reproducible deployment and verification of the three-route VPS baseline.

Current separation:

- three-route baseline: proven;
- Foxy recipient distribution and persistent delivery: proven;
- perfect VPN-off personal Landing UX: partial;
- Reproducible Node Builder clean-room acceptance: still STOP in its separate track.

Do not delay the first commercial VPS offer indefinitely waiting for perfect Landing UX; direct Happ delivery keys are already a working fallback.

## Immediate new-chat instruction

After reading the canonical files, ask which bounded next task is intended:

1. one final VPN-off Landing/HTTP2 diagnostic or fix gate;
2. formal Foxy Wi-Fi acceptance;
3. legacy cleanup;
4. return to Reproducible Node Builder and commercial service readiness.

Do not touch Space Signal or begin an unrelated project track automatically.
