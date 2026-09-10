# Foxy Baby — recipient delivery and persistence checkpoint

**Checkpoint date:** 2026-09-10  
**Scope:** recipient isolation, subscription delivery, persistence and current zero-state bootstrap boundary  
**Verdict:** `RECIPIENT DELIVERY + REBOOT PERSISTENCE PASS / ZERO-STATE LANDING PARTIAL`

## Evidence boundary

This is a sanitized public checkpoint. It intentionally omits working server addresses and hostnames, SSH metadata, selected ports, tunnel identifiers, recipient names, UUIDs, REALITY material, Hysteria credentials, subscription and landing tokens, client URIs, working HTTPS URLs, SNI, certificate/private-key material, raw configurations and secret-bearing logs.

Raw recipient material, runtime manifests, local bundles and rollback backups remain private and outside Git.

This checkpoint does not replace the accepted `PP-LAB-01` G2/G3/G4 baseline and does not by itself promote Foxy Baby to a second formal G2/G3/G4 node.

## Starting point

The earlier Foxy Baby maintenance checkpoint had already established:

- key-only SSH administration;
- password and direct-root SSH disabled;
- default-drop inbound firewall persistence;
- reboot recovery for the three independently selectable transport profiles;
- operational Android use of Route I, Route II and Route III after reboot.

The work recorded here starts from that accepted maintenance state and adds recipient delivery without redesigning the three route runtimes.

## Recipient isolation

`FACT` — three independent recipient identities were provisioned.

`FACT` — each recipient received independent authentication material for all three routes and an independent high-entropy subscription identity.

`FACT` — recipient material is held in a root-only server-side catalog; the public repository does not contain the values.

`FACT` — one recipient credential set was rotated as a live isolation test.

`FACT` — after that rotation, the old credentials for that recipient were rejected, the new credentials worked, and the other two recipients remained unaffected.

`DECISION` — independent revoke/rotation is part of the recipient-delivery acceptance model; a recipient must be removable without rotating every other user.

## Operator credential cutover

`FACT` — the previously shared Foxy Baby operator access material was replaced by a new owner-only credential set.

`FACT` — the new owner credentials were validated before the old shared credentials were revoked.

`FACT` — after revocation, the old shared credentials no longer authenticated, the new owner credentials worked, and all three recipient credential sets remained unaffected.

`FACT` — the resulting authentication structure is one owner identity plus three independent recipient identities.

## Subscription delivery

`FACT` — each recipient has one subscription that composes exactly three profiles: two VLESS-based routes and one Hysteria2 route.

`FACT` — a stable HTTPS delivery path was introduced through a Cloudflare Named Tunnel while the HTTP origins remained loopback-only on the VPS.

`FACT` — temporary Quick Tunnel delivery was retained only during migration/rollback validation and is not the accepted persistent delivery transport.

`FACT` — the final delivery design uses separate persistent loopback origins for the personal landing and the subscription endpoint.

`FACT` — both persistent origin services are configured for boot persistence.

`FACT` — the Named Tunnel connector is also configured for boot persistence.

`FACT` — the connector credential is stored root-only and was verified absent from the systemd unit arguments and journal output used for acceptance.

## Stable HTTPS acceptance

`FACT` — the stable subscription endpoint returned all three recipient subscriptions successfully.

`FACT` — the live payload for each recipient matched the corresponding canonical server-side payload byte-for-byte at acceptance time.

`FACT` — composition remained exactly three profiles per recipient.

`FACT` — subscription metadata included a human-readable profile title; localized display labels, emoji and country-flag presentation were validated in Happ without changing transport/authentication fields.

`FACT` — an unknown subscription token returned `404`.

`FACT` — the three VPN route units remained active and their route configuration hashes/regression checks were unchanged during the delivery work.

## TLS hostname correction during migration

`FACT` — an initially selected nested subscription hostname was found not to be covered by the zone's active edge certificate.

`FACT` — the failure was isolated as an edge-certificate coverage problem rather than a route or origin failure.

`FACT` — a first-level sibling hostname was introduced on the same persistent tunnel and passed certificate coverage and HTTPS acceptance.

`DECISION` — the invalid nested hostname is not an accepted recipient endpoint and must not be used in client material.

## Persistent-origin migration lessons

`FACT` — the earlier transient subscription and landing origins each shared a supervisor/cgroup with their own Quick Tunnel process.

`FACT` — the first persistence migration correctly stopped at preflight when this origin/tunnel coupling was discovered; no write was performed in that stopped attempt.

`FACT` — the persistent origins were then introduced additively in parallel rather than replacing the working fallback first.

`FACT` — the new subscription origin initially accepted the service start but dropped requests because its Python handler defined a method named `headers`, colliding with `BaseHTTPRequestHandler`'s instance attribute of the same name.

`FACT` — the smallest handler-only correction restored valid subscription responses without changing routes, firewall or tunnel configuration.

`FACT` — the stable Named Tunnel routes were switched to the new persistent origins only after the new origins passed direct loopback checks.

## Controlled reboot persistence

A real controlled reboot was performed after the persistent origins and Named Tunnel route switch.

`FACT` — boot identity changed, proving that a new boot occurred.

`FACT` — Route I, Route II and Route III returned after boot.

`FACT` — both persistent delivery origins returned and remained loopback-only.

`FACT` — the Named Tunnel connector returned.

`FACT` — stable landing HTTPS returned after reboot.

`FACT` — all three stable subscription endpoints returned after reboot.

`FACT` — all three post-reboot live subscriptions still matched canonical payloads and retained the expected three-profile composition and profile-title metadata.

`FACT` — unknown-token handling remained `404`.

`FACT` — failed systemd units after this controlled reboot: `0`.

`DECISION` — recipient delivery persistence is accepted as PASS for this checkpoint.

## Direct Happ-key result

`FACT` — the direct Happ deep-link shape used for accepted recipient distribution is one deep link containing the recipient's stable HTTPS subscription URL.

`FACT` — three separate recipient deep links were generated locally from private server-side state and confirmed working by the owner.

`FACT` — each direct key expands into the intended three-profile subscription.

`FACT` — a bare subscription token by itself is not a usable Happ or Amnezia import key; only the complete client deep link / subscription URL form is accepted for distribution.

`FACT` — earlier Happ observations included a misleading timeout notification and a transient technical-hostname title before a refresh, even though the subscription had already been added. Later direct-key attempts also completed cleanly. This UI behavior is recorded as client-side variability, not as a route failure.

## Personal landing implementation

`FACT` — the personal landing keeps its landing token in the URL fragment on initial page load, then posts that value same-origin to resolve the recipient subscription.

`FACT` — the landing button ultimately invokes the direct Happ add deep link with the resolved HTTPS subscription URL.

`FACT` — a read-only implementation audit found no alternate `happ://import` form, no whole-URL `encodeURIComponent` transformation and no evidence that the landing was intentionally passing its own HTML URL to Happ.

`DECISION` — do not redesign the landing or VPN infrastructure without a concrete failing boundary.

## Current zero-state mobile boundary

The remaining product issue is narrower than the recipient/subscription system itself.

`FACT` — with another VPN path already active, the personal landing and direct Happ import operate normally.

`FACT` — on one Android mobile-data path with the VPN switched off, two browsers displayed an effectively blank landing page.

`FACT` — an autonomous VPN-off client probe reached HTTPS and received HTTP `200` plus `text/html`, but received zero body bytes before timing out.

`FACT` — a later protocol comparison showed that an HTTP/1.1 request began receiving response-body bytes, while an HTTP/2 request received `200` headers and then stalled at zero body bytes until timeout. The HTTP/1.1 run itself ended early because the test attempted to write to a path not present in that Termux environment, so it is evidence of body delivery beginning, not a complete HTTP/1.1 acceptance.

`FACT` — a direct loopback probe of the Foxy landing origin returned `200`, a declared `Content-Length` matching the full body, no transfer/content encoding anomaly, and the complete body.

`FACT` — a read-only Cloudflare control-plane comparison against the already working PP-LAB One-Tap pattern found no explanatory difference in tunnel health, proxied DNS path, Access, Workers, custom WAF, redirect, transform, cache/configuration or origin rules. Request trace returned `200` and matched only built-in normalization/cache-key phases.

`FACT` — no target request event with edge/origin byte counts was found in the available dashboard view.

`HYPOTHESIS` — the unresolved boundary is now most likely in the VPN-off client/mobile transport path to the Cloudflare edge, with HTTP/2 behavior a leading discriminator; the current evidence does not prove whether the carrier path, edge delivery behavior or another transport-layer interaction is causal.

## Response-body-buffering experiment status

`FACT` — a narrowly scoped Cloudflare Configuration Rule using response-body streaming/buffering settings was proposed as one final experiment for the landing path only.

`FACT` — two Browser Assistant attempts stopped before the setting availability check because Cloudflare dashboard navigation/Chrome control timed out.

`FACT` — both attempts ended with `WRITE_PERFORMED=NO`; no response-body-buffering rule was created.

`FACT` — the owner stopped the session before any manual UI deployment was performed.

`DECISION` — a future chat must not assume that this Cloudflare experiment has already been applied.

## Formal acceptance boundary

`FACT` — the private Android/mobile route matrix for Foxy Baby has passed repeated route checks, restart/stop-start isolation and regression work performed during the recipient-delivery program.

`FACT` — the full formal Wi-Fi matrix has not yet been completed for Foxy Baby under the canonical experiment protocol.

`DECISION` — Foxy Baby remains not claimed as a second formal G2/G3/G4 node until the missing target-network acceptance is completed and separately recorded.

The zero-state landing problem is also a bootstrap/user-experience issue; it does not invalidate the working direct subscription/Happ keys or the underlying I/II/III routes.

## Current verdict

```text
RECIPIENT_COUNT=3
INDEPENDENT_RECIPIENT_AUTH=PASS
INDEPENDENT_ROTATION_REVOKE=PASS
OLD_SHARED_OPERATOR_ACCESS=REVOKED
OWNER_PLUS_RECIPIENT_MODEL=PASS
STABLE_SUBSCRIPTION_3_OF_3=PASS
CANONICAL_LIVE_MATCH_3_OF_3=PASS
THREE_PROFILE_COMPOSITION_3_OF_3=PASS
DIRECT_HAPP_KEYS=PASS
PERSISTENT_LOOPBACK_ORIGINS=PASS
NAMED_TUNNEL_PERSISTENCE=PASS
CONTROLLED_REBOOT_DELIVERY=PASS
FAILED_SYSTEMD_UNITS_POST_REBOOT=0
ZERO_STATE_LANDING_VPN_OFF=PARTIAL
HTTP2_BODY_STALL_ON_TESTED_MOBILE_PATH=OBSERVED
RESPONSE_BODY_BUFFERING_RULE=NOT_APPLIED
FOXY_FORMAL_WIFI_MATRIX=PENDING
FORMAL_SECOND_NODE_G2_G3_G4=NOT_CLAIMED
```

## Next useful actions

1. Decide whether to spend one more bounded gate on the VPN-off HTTP/2 landing-path experiment or freeze the landing as a known bootstrap limitation and use the already working direct Happ keys.
2. Run the missing Foxy Baby formal Wi-Fi acceptance when an actual Wi-Fi target network is available; do not rerun the already proven mobile matrix without a concrete reason.
3. Remove obsolete transient/legacy delivery artifacts only under a separate cleanup gate after confirming they are no longer rollback dependencies.
4. Keep the reproducible Builder track separate: fast clean-room deployment remains unproven until Builder acceptance advances beyond its existing STOP checkpoint.
