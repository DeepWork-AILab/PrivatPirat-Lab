# Foxy Baby — review of direct-delivery closure

**Review date:** 2026-09-29
**Source checkpoint:** 2026-09-23
**Status:** SOURCE REVIEW / HISTORICAL OPERATIONAL EVIDENCE

## Provenance

FACT — This record summarizes the owner's private Google Drive document “Foxy Baby — Production Closure & Evidence”, checkpoint 2026-09-23. The source was read during this documentation review. Raw operational evidence is retained privately; its server metadata, personal links, recipient identities and configuration values are deliberately not reproduced here.

This is a review of an existing checkpoint, not a new live replay.

## What the source records

- FACT — Direct HTTPS delivery through a Caddy front door replaced the prior edge-dependent front door for the new release. The older tunnel path was retained pending a separate legacy decision.
- FACT — Nine personal Landings reached the source's production gate; the source records VPN-off tests on two mobile networks.
- FACT — Each personal subscription contained three selectable routes. Display-label changes were documented separately from authentication and transport parameters.
- FACT — A controlled reboot was followed by service, TLS, Landing/subscription and download-mirror checks.
- FACT — Route I/II and real browser egress for Route III were recorded as working; Route III showed an intermittent client-interface TLS error despite successful browser data path in two independent profiles.
- FACT — Termux on the tested phone bypassed the client's routing policy. Its request result was therefore not evidence of the browser's VPN egress.

## Remaining limits

- TODO — Deliver the new links, then authorize and verify legacy revoke/decommission separately. The source does not prove these later steps complete.
- TODO — Native Apple-client launch remained untested.
- HYPOTHESIS — The cause of the transient client TLS message remains unproven.
- FACT — This closure does not supply a newly completed formal Wi-Fi G2/G3/G4 matrix for Foxy and does not change the Builder STOP.
- FACT — PP-LAB-01's later owner report is evidence for that node; it does not close Foxy's remaining tasks.

## Relationship to older evidence

The [2026-09-10 delivery checkpoint](FOXY-BABY-RECIPIENT-DELIVERY-CHECKPOINT-2026-09-10.md) remains valid historical evidence. Its stalled Landing body is not the latest documented front-door status. A successful replacement path does not establish the root cause of the old symptom.

## Recovery lesson

Test the actual application's path before repairing transport based on an interface message. Record which process traverses the VPN and which bypasses it. Preserve the distinction between operational recovery and proven root cause.
