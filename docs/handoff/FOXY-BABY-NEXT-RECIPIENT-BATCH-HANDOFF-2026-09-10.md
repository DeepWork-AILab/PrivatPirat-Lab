# Foxy Baby — next recipient batch handoff

**Checkpoint date:** 2026-09-10  
**Project:** PrivatPirat Lab  
**Status:** prepared workflow; not yet executed

## Purpose

Foxy Baby is intentionally used as a shareable node for friends and trusted recipients. The current three-recipient set is not the final capacity target.

The next requested operation is to add **three genuinely new recipients** and produce **three new Happ delivery keys**, while preserving all three existing recipients exactly as they are.

This is different from reprinting the three current keys. It is a new bounded provisioning run and therefore requires a fresh explicit R3 gate before any server change.

## Current fact boundary

At this checkpoint:

```text
CURRENT_RECIPIENTS=3
NEXT_BATCH_REQUESTED=3
EXPECTED_TOTAL_AFTER_SUCCESS=6
NEXT_BATCH_EXECUTED=NO
```

Do not claim six recipients until the run is actually completed and verified.

## Required behavior for the next chat

If the owner says:

> «Создай ещё три новых пользователя Foxy Baby и дай мне три новых Happ-ключа»

then the assistant should:

1. Read the current canonical Foxy handoff/evidence and `AGENTS.md` first.
2. Perform a read-only preflight of the current recipient state before any change.
3. Present one R3 change packet covering exactly one new batch of three recipients.
4. Preserve the three current recipients and the owner identity unchanged.
5. Create three new independent recipient identities using the already accepted recipient model rather than redesigning the route architecture.
6. Verify that each new recipient receives the intended three-profile subscription and that the previous three recipients remain unaffected.
7. Keep firewall, tunnel, route architecture and unrelated delivery components outside the write scope unless a separately approved blocker requires otherwise.
8. Keep all private values outside GitHub and chat.
9. After successful verification, print the three new Happ keys only in the owner's local Termux session.
10. If current private state does not match the expected three-recipient baseline, STOP instead of trying to repair or infer state automatically.

## Target result

The desired acceptance markers for that future run are:

```text
RECIPIENTS_BEFORE=3
NEW_RECIPIENTS=3
RECIPIENTS_AFTER=6
NEW_HAPP_KEYS=3
NEW_RECIPIENTS_I_II_III=PASS
OLD_RECIPIENTS_UNCHANGED=PASS
OWNER_IDENTITY_UNCHANGED=PASS
INDEPENDENT_ROTATION_MODEL=PRESERVED
```

These are target markers only, not current facts.

## Security boundary

No working address, hostname, port, token, UUID, credential, recipient name, client URI, subscription URL, SNI or complete private configuration belongs in this public handoff.

The exact values and any generated Happ keys must remain on the private operator/server side and be shown only locally to the owner when the future provisioning run is complete.

## Relationship to the main Foxy handoff

This addendum supplements `docs/handoff/FOXY-BABY-OPERATOR-HANDOFF-2026-09-10.md`.

The main handoff remains authoritative for the current three-recipient delivery state, persistent Named Tunnel/origins, reboot result, Landing HTTP/2 investigation, Wi-Fi acceptance boundary and Builder/commercial separation.

This file adds one operational clarification only: **the next recipient task is to expand from three to six independent recipients by adding one new batch of three, not to regenerate the existing three keys.**
