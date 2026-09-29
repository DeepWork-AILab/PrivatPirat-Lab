# PrivatPirat Lab

## Operator name

- Preferred form of address in all non-official project interactions: **Брат Димитрий**.
- Use **«Дмитрий»** only when an official/legal-document name is required.
- Do not shorten, substitute, or normalize this form of address in operator-facing communication.

Evidence-driven VPN lab: three independently selectable transport profiles on a single VPS, tested against an explicit acceptance protocol rather than declared working from service state alone.

**Core baseline:** `COMPLETE / PASS`  
**Repository:** `ACTIVE R&D`  
**Primary accepted node:** `PP-LAB-01`  
**Source of truth:** GitHub `main`

## What is complete

The original PrivatPirat experiment is complete.

| Gate | Route | Result |
|---|---|---|
| `G2` | VLESS RAW/TCP REALITY/Vision | `PASS` |
| `G3` | VLESS XHTTP REALITY | `PASS` |
| `G4` | Hysteria2 TLS/QUIC/UDP | `PASS` |

For the accepted three-route baseline, the project verified real client data path rather than relying on `active`, `connected`, handshake, ping or a single successful page load.

Acceptance evidence includes:

- DNS resolution and leak-oriented checks;
- HTTP and HTTPS data path;
- two independent exit-IP checks;
- repeated clean reconnects;
- Android/mobile and Wi-Fi coverage;
- server restart recovery;
- per-route stop/start recovery and isolation;
- regression testing of previously accepted routes after adding a new route.

After `PP-LAB-III` was added, both earlier routes passed the required regression matrix on Wi-Fi and mobile. The canonical protocol therefore records the three-route baseline as completed.

See:

- [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md)
- [`docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md`](docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md)
- [`docs/evidence/PP-LAB-II-G3-PASS-2026-08-29.md`](docs/evidence/PP-LAB-II-G3-PASS-2026-08-29.md)
- [`docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md`](docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md)

## Architecture

```text
client manually selects one route
                │
         PP-LAB-01 / one IP
         ├─ TCP/<PORT_I>   → xray.service        → PP-LAB-I
         ├─ TCP/<PORT_II>  → xray@pp-lab-ii     → PP-LAB-II
         └─ UDP/<PORT_III> → pp-lab-iii.service → PP-LAB-III
```

The three profiles provide transport diversity, not host-level high availability. One VPS remains one failure domain and all three profiles share the same provider egress identity.

`PP-LAB-I` and `PP-LAB-II` both use VLESS but differ by transport. `PP-LAB-III` is Hysteria2 over TLS/QUIC/UDP.

## Why this repository exists

The project was designed to answer a narrower question than “can a VPN be installed?”:

> Can three independent transport profiles be built, tested, recovered and regressed under a repeatable evidence protocol without confusing configuration state with a working end-to-end data path?

The working method is intentionally conservative:

- facts are separated from decisions, hypotheses and TODOs;
- read-only observation comes before changes;
- changes require expected result, verification, backup, rollback and stop condition;
- unexpected outcomes stop progression instead of triggering chains of speculative fixes;
- public evidence is sanitized and excludes operational secrets.

Project operating rules are defined in [`AGENTS.md`](AGENTS.md) and [`SECURITY.md`](SECURITY.md).

## Acceptance model

A route receives `PASS` only when the required client-side data path is demonstrated under the current protocol baseline. Service state is only intermediate evidence.

The protocol requires, where applicable:

1. a clean client start with one explicitly selected route;
2. DNS verification;
3. HTTP and HTTPS through independent endpoints;
4. two independent exit-IP services agreeing with the expected server egress;
5. at least three clean reconnect repetitions;
6. recovery after restart of the server unit;
7. stop/start isolation from previously accepted routes;
8. regression of earlier routes after a new route is introduced.

Full criteria: [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md).

## Accepted primary node

`PP-LAB-01` remains the canonical personal PrivatPirat node.

Confirmed platform baseline:

- Ubuntu 24.04 LTS, `x86_64`;
- approximately 1 vCPU, 1 GB RAM and 14 GB root disk at initial inventory;
- one public provider address, intentionally omitted from the repository;
- key-only SSH after maintenance hardening;
- three accepted PrivatPirat route runtimes;
- auxiliary IPv6-only Cloudflare WARP egress retained separately from the three accepted routes.

The primary-node role decision is documented in [`docs/evidence/PP-LAB-PRIMARY-NODE-ROLE-DECISION-2026-09-08.md`](docs/evidence/PP-LAB-PRIMARY-NODE-ROLE-DECISION-2026-09-08.md).

## One-Tap delivery

A persistent One-Tap bootstrap path has also reached a separate operational `PASS` checkpoint.

Confirmed on 2026-09-08:

- the delivery origin remained loopback-only;
- Cloudflare Named Tunnel replaced the temporary Quick Tunnel transport;
- the stable custom-domain HTTPS endpoint survived a controlled VPS reboot;
- the subscription still contained exactly two VLESS profiles and one Hysteria2 profile;
- a zero-state Happ refresh succeeded after reboot;
- the previously accepted I/II/III route configurations were not changed by this delivery checkpoint.

This is a bootstrap/persistence result, not a new G2/G3/G4 route acceptance.

Evidence: [`docs/evidence/PP-LAB-ONE-TAP-NAMED-TUNNEL-PASS-2026-09-08.md`](docs/evidence/PP-LAB-ONE-TAP-NAMED-TUNNEL-PASS-2026-09-08.md).

## Recipient delivery layer

A separate additive recipient checkpoint was completed on `PP-LAB-01` on 2026-09-13:

- four independent friend-recipient identities were added without replacing the owner identity;
- the client subscription header is `DeepWork AILab`;
- the three visible route labels are `🇺🇸 Privat 🏴‍☠️ Pirat I`, `🇺🇸 Privat 🏴‍☠️ Pirat II`, and `🇺🇸 Privat 🏴‍☠️ Pirat III`;
- direct Happ subscription links were the verified distribution path at that checkpoint;
- an active/clickable Landing-based delivery flow was deferred at that checkpoint.

On 2026-09-29 the owner reported a later operational checkpoint: every current personal recipient link, including the newly added recipient link, opened with VPN disabled; the Landing loaded; and the installation flow completed successfully. This updates the delivery-layer record without creating a new formal route acceptance.

Evidence:

- [`docs/evidence/PP-LAB-01-FOUR-FRIEND-RECIPIENT-CHECKPOINT-2026-09-13.md`](docs/evidence/PP-LAB-01-FOUR-FRIEND-RECIPIENT-CHECKPOINT-2026-09-13.md)
- [`docs/evidence/PP-LAB-01-RECIPIENT-DELIVERY-OWNER-REPORT-2026-09-29.md`](docs/evidence/PP-LAB-01-RECIPIENT-DELIVERY-OWNER-REPORT-2026-09-29.md)

## Secondary node: Foxy Baby

A provider-diverse secondary VPS has been deployed and hardened as a separate operational node.

The earlier maintenance checkpoint established key-only administration, default-drop inbound firewall policy, reboot persistence and post-reboot use of all three transport profiles.

The historical 2026-09-10 recipient-delivery checkpoint added a stronger product layer without redesigning the three route runtimes:

- one owner-only identity plus three independent recipient identities;
- independent recipient authentication across all three routes;
- independent recipient subscription identities;
- live revoke/rotation proof for one recipient without affecting the other two;
- old shared operator access revoked after owner-only replacement credentials were proven;
- stable HTTPS recipient delivery through a persistent Cloudflare Named Tunnel;
- separate loopback-only persistent origins for Landing and Subscription;
- three-recipient subscription acceptance with canonical/live exact matching and expected three-profile composition;
- direct Happ delivery keys confirmed working;
- controlled-reboot persistence for routes, delivery origins and Named Tunnel connector;
- failed systemd units after the delivery reboot: `0`.

At that 2026-09-10 checkpoint, one product boundary remained partial: on one tested Android/mobile zero-state path with VPN off, the personal Landing returned HTTP success headers but the HTTP/2 response body stalled, while a forced HTTP/1.1 probe began receiving body bytes. The direct origin returned the complete declared body and a read-only Cloudflare control-plane comparison found no explanatory hostname-specific rule difference. The exact carrier/edge/transport cause remains unproven, so no root cause is claimed.

That historical checkpoint retained direct Happ keys as a distribution fallback. The later 2026-09-23 private Production Closure records a new direct HTTPS front door, nine personal Landings, VPN-off mobile delivery and reboot persistence. This supersedes the old Landing symptom as the latest documented delivery status; it does not prove the cause of the earlier HTTP/2 stall.

The later closure still leaves recipient distribution, separately authorized legacy revoke/decommission and native Apple-client verification open. These are not silently marked complete by the 2026-09-29 owner report about PP-LAB-01.

Foxy Baby is deliberately **not** claimed as another formal G2/G3/G4 node yet: the private Android/mobile matrix has passed, but the complete formal Wi-Fi target-network matrix remains pending under the canonical protocol.

Evidence and continuation:

- [`docs/evidence/FOXY-BABY-DIRECT-DELIVERY-SOURCE-REVIEW-2026-09-29.md`](docs/evidence/FOXY-BABY-DIRECT-DELIVERY-SOURCE-REVIEW-2026-09-29.md) — sanitized review of the later private 2026-09-23 closure

- [`docs/evidence/FOXY-BABY-HARDENING-POST-REBOOT-2026-09-04.md`](docs/evidence/FOXY-BABY-HARDENING-POST-REBOOT-2026-09-04.md)
- [`docs/evidence/FOXY-BABY-RECIPIENT-DELIVERY-CHECKPOINT-2026-09-10.md`](docs/evidence/FOXY-BABY-RECIPIENT-DELIVERY-CHECKPOINT-2026-09-10.md)
- [`docs/handoff/FOXY-BABY-OPERATOR-HANDOFF-2026-09-10.md`](docs/handoff/FOXY-BABY-OPERATOR-HANDOFF-2026-09-10.md)
- [`docs/field-notes/FOXY-BABY-DELIVERY-LESSONS-AND-ARTICLE-SEEDS-2026-09-10.md`](docs/field-notes/FOXY-BABY-DELIVERY-LESSONS-AND-ARTICLE-SEEDS-2026-09-10.md)

## Reproducible Node Builder

`PrivatPirat Reproducible Node Builder v0.1` is the main unfinished R&D track.

The Builder is implemented as a Python + system OpenSSH workflow with unit/regression coverage and scoped rollback behavior. However, its first real clean-room acceptance exposed verifier defects and stopped during Route I data-path verification.

Current Builder verdict:

```text
BUILDER_ACCEPTANCE=STOP
ROUTES_ACCEPTED=NONE
CLIENT_BUNDLE=NOT_READY
FORMAL_MULTI_NETWORK_ACCEPTANCE=NOT_RUN
NEXT_PHASE=LOCAL_VERIFIER_DIAGNOSIS
```

The failed live attempts rolled Route I back successfully and did not change the already accepted manual G2/G3/G4 baseline.

Current evidence: [`docs/evidence/PP-LAB-BUILDER-CLEANROOM-STOP-2026-08-31.md`](docs/evidence/PP-LAB-BUILDER-CLEANROOM-STOP-2026-08-31.md).

The Builder is therefore presented as **active engineering work**, not as a finished deployment product.

## Current maintenance and R&D

The completed three-route baseline is intentionally separated from later work.

**Immediate priority after the current Foxy Baby / PrivatPirat completion gate:** remove the owner from the manual transport path between the control AI and executors. The target operator UX is:

> From the smartphone, the owner states the end goal in ordinary language → the system turns it into an executable task → selects the appropriate executor → asks for one approval only when a risky write requires it → executes → verifies the result → returns the finished outcome to the owner.

Success means the owner is no longer required to copy commands and results manually between ChatGPT and Termux, Codex/OpenCode, cloud/VPS executors, or equivalent execution surfaces during normal work. The terminal remains available for exceptional diagnostics and recovery, not as the routine message bus. This automation is the first priority after the current Foxy Baby / PrivatPirat work is brought to the agreed completion state; it should reuse the existing control, approval, verification and rollback model rather than introduce a new AI framework without demonstrated need.

Open work includes:

- remediation/rotation of one historical PP-LAB-I client credential that appeared in local shell history; tracked in GitHub issue `#7`, with a [preparation runbook](docs/handoff/ISSUE-7-CREDENTIAL-ROTATION-PREPARATION-2026-09-29.md);
- local diagnosis and regression coverage for the Builder verifier before another live clean-room run;
- confirm Foxy recipient distribution before a separately authorized legacy revoke/decommission; diagnose the historical HTTP/2 stall only if it becomes relevant again;
- completion of Foxy Baby's formal Wi-Fi acceptance before any second-node G2/G3/G4 claim;
- cleanup of obsolete transient Foxy delivery artifacts only after proving they are no longer rollback dependencies;
- capacity and resilience planning for the primary personal node and additional nodes.

These items do not change the recorded `G2/G3/G4 PASS` of the original experiment unless new regression evidence demonstrates an actual failure.

## Documentation review and continuity

- [Recovery knowledge assessment](docs/field-notes/ENGINEERING-RECOVERY-KNOWLEDGE-ASSESSMENT-2026-09-29.md) — source-linked reusable lessons and limits of the bot search.
- [Article backlog review](docs/field-notes/ARTICLE-BACKLOG-REVIEW-2026-09-29.md) — preserves the author's existing editorial holds.
- [Audit discrepancies](docs/field-notes/DOCUMENTATION-AUDIT-2026-09-29.md) — outstanding instruction-scope conflict and evidence limits.

## Security boundary

The public repository intentionally excludes working operational material.

Do not commit or publish:

- passwords, private SSH keys or recovery material;
- UUIDs or client identifiers;
- REALITY private keys or Short IDs;
- Hysteria2 passwords or TLS private keys;
- working connection URIs or subscription URLs;
- complete client/server configurations containing operational values;
- raw secret-bearing logs;
- working REALITY target/SNI;
- public server/SSH metadata unless explicitly approved for a specific public record.

Sanitized evidence records methods, versions, classes of networks and PASS/FAIL observations instead of deployable secrets.

## Repository map

- [`AGENTS.md`](AGENTS.md) — operating rules and safety gates
- [`SECURITY.md`](SECURITY.md) — public security boundary
- [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md) — formal acceptance protocol
- [`docs/evidence/`](docs/evidence/) — sanitized checkpoints and PASS/STOP records
- [`docs/field-notes/`](docs/field-notes/) — lessons and narrative field notes
- [`docs/handoff/`](docs/handoff/) — bounded handoff records
- [`scripts/`](scripts/) — Builder and supporting automation
- [`tests/`](tests/) — Builder regression tests

## Relationship to other projects

PrivatPirat Lab is a separate public laboratory project. It does not rename, replace or modify Space Signal, and `PP-LAB-01` is not automatically promoted into any external architecture by results recorded here.

## Upstream references

Implementation details are rechecked against primary upstream sources before changes:

- [Xray-core releases](https://github.com/XTLS/Xray-core/releases)
- [Project X: REALITY](https://xtls.github.io/en/config/transports/reality.html)
- [Project X: XHTTP](https://xtls.github.io/en/config/transports/xhttp.html)
- [Hysteria 2 releases](https://github.com/apernet/hysteria/releases)
- [Hysteria 2 server documentation](https://v2.hysteria.network/docs/getting-started/Server/)

Historical configurations are treated only as structural references; their operational values are never reused automatically.

## License

No license has been selected yet. Public availability of this repository does not by itself grant permission to copy, redistribute or create derivative works.
