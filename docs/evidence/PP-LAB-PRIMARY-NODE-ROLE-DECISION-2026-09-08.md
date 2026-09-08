# PP-LAB-01 — primary personal node role decision

**Date:** 2026-09-08  
**Scope:** PrivatPirat Lab node-role and capacity planning only  
**Status:** `ROLE DECISION / CAPACITY TODO`

## Decision

- `DECISION` — `PP-LAB-01` remains the primary personal PrivatPirat node for the owner.
- `DECISION` — the accepted `PP-LAB-I + PP-LAB-II + PP-LAB-III` baseline on this node remains the canonical personal VPN path and is not intended for recipient distribution.
- `DECISION` — the existing WARP configuration remains an auxiliary IPv6-only egress path; it is not promoted to a fourth recipient/user-facing route by this decision.

## Capacity and redundancy plan

- `TODO` — evaluate and, after separate provider-side approval, upgrade the primary node from the current lower-cost plan to a plan with an owner target budget of approximately USD 8/month. The exact provider plan, resulting resources, billing amount and migration behavior must be verified before purchase or change.
- `TODO` — acquire an additional VPS/location advertised in the New York metropolitan area as a separate resilience node. Exact provider, datacenter, network/ASN and role are not yet fixed by this record.
- `FACT` — a second VPS in the same provider or metropolitan area must not be labeled provider-diverse unless provider/network independence is separately verified.

## Safety boundary

This record authorizes documentation of the role and plan only. It does not authorize a provider purchase, billing change, VPS resize/reinstall, migration, DNS change, route change or credential rotation.

No working server address, SSH metadata, client identifiers, credentials, subscription URL or other operational secret is included in this public record.
