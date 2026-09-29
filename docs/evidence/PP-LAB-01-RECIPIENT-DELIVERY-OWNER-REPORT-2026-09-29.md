# PP-LAB-01 recipient delivery — owner-reported operational checkpoint

**Date:** 2026-09-29  
**Status:** `OWNER-REPORTED OPERATIONAL CHECKPOINT`  
**Scope:** personal Landing, recipient links and installation flow on the existing `PP-LAB-01` delivery layer

## Why this record exists

The earlier recipient checkpoint recorded direct subscription delivery while the clickable Landing flow was still deferred. On 2026-09-29 the owner reported that the current delivery flow was working for all current recipients, including the newly added recipient.

This public record preserves that operational outcome without publishing recipient identities or live delivery material.

## Owner-reported observations

The owner directly reported that:

- every current personal recipient link opened with VPN disabled;
- the newly added recipient's link also opened with VPN disabled;
- the personal Landing loaded;
- the installation flow completed successfully;
- no active use of the temporary secondary-provider path remained.

## Evidence classification

This is a direct owner report from real recipient-facing use. It is stronger than an implementation intention or a service-status observation, but it is not a repeated formal acceptance run captured by the repository protocol.

The checkpoint therefore updates the recorded state of the delivery product layer. It does not create a new `G2`, `G3` or `G4` route acceptance and does not replace the earlier route evidence.

## What is established

- The current personalized delivery links are usable from the reported VPN-off client state.
- The Landing and installation path are operational in the reported real-world use.
- The added recipient is included in the working delivery set.
- The temporary secondary-provider path is no longer part of the active operating workflow.

## What is not established by this record

This checkpoint does not claim:

- a fresh independent replay of DNS, HTTP, HTTPS, exit-IP, reconnect, restart and route-isolation checks for every recipient;
- a new clean-room Builder acceptance;
- a root cause for any earlier transient client or Landing behavior;
- continued operation beyond the reported observation window;
- any deployable configuration, address, credential or recipient identifier.

## Naming boundary

`PrivatPirat Lab` remains the engineering and evidence matrix name. `LilFox Hacker` may remain the user-facing project or delivery name. No repository-wide rename is required by this checkpoint.

## Security boundary

The record intentionally omits:

- recipient names and account identifiers;
- personal Landing and subscription URLs;
- server addresses, hostnames and ports;
- client credentials, UUIDs, passwords and keys;
- raw client or server logs.

## Relationship to prior evidence

This checkpoint extends the delivery history recorded in:

- [PP-LAB-01 four-friend recipient checkpoint](PP-LAB-01-FOUR-FRIEND-RECIPIENT-CHECKPOINT-2026-09-13.md);
- [PP-LAB One-Tap Named Tunnel PASS](PP-LAB-ONE-TAP-NAMED-TUNNEL-PASS-2026-09-08.md).

Those records remain the source for their respective implementation and acceptance details.
