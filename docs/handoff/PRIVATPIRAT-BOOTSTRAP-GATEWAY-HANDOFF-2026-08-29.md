# PrivatPirat Bootstrap Gateway v0.1 — Handoff

**Checkpoint date:** 2026-08-29  
**Project:** DeepWork AIHub / PrivatPirat AILab / PrivatPirat Lab  
**Status:** ready to continue in a new project chat  
**Next workstream:** `PrivatPirat Bootstrap Gateway v0.1`

## 1. Why this handoff exists

The current chat completed a large continuous sequence: PP-LAB-I / II / III acceptance, one-subscription assembly, Happ deep-link proof, and bootstrap delivery experiments. To reduce context load, further work should continue in a new chat inside the same project, using this handoff and the canonical sources below rather than reconstructing history from chat memory.

## 2. Canonical sources

1. GitHub source of truth: `DeepWork-AILab/PrivatPirat-Lab`, branch `main`.
2. Experiment protocol: `docs/EXPERIMENT_PROTOCOL.md`.
3. G4 final evidence: `docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md`.
4. One-Tap checkpoint: `docs/evidence/PP-LAB-ONE-TAP-PROTOTYPE-v0.1-2026-08-29.md`.
5. DeepWork AIHub canonical architecture: Google Doc `DeepWork AIHub — Integration Registry v0.2`.
6. Repository `AGENTS.md` remains mandatory for all server work.

If chat memory conflicts with the current canonical documents, the documents win.

## 3. Accepted VPN baseline

`PP-LAB-01` has three independently selectable accepted routes:

- `PP-LAB-I` — VLESS / TCP / REALITY / Vision — PASS.
- `PP-LAB-II` — VLESS / XHTTP / REALITY — PASS.
- `PP-LAB-III` — Hysteria2 / TLS / QUIC / UDP — PASS.

All three passed the project acceptance baseline including mobile/Wi-Fi data path, reconnect repetitions, restart recovery, stop/start isolation and required regressions. Operational secrets are intentionally absent from this document.

## 4. One-Tap result

The following product interaction is proven:

`one subscription link -> Happ -> one subscription -> Privat Pirat I + II + III`

Happ successfully created one `PrivatPirat AILab` subscription containing all three profiles when the subscription endpoint was reachable.

Verdict:

- `One-Tap mechanics = FUNCTIONAL PASS`.
- `Cloudflare Quick Tunnel bootstrap = FAIL for production suitability`.

Reason: on the target Android/mobile direct-connectivity state, Happ timed out while fetching the temporary `trycloudflare.com` subscription endpoint. The same subscription immediately updated and expanded correctly when another VPN path was enabled. Happ subscription fragmentation did not remove the direct-connectivity timeout.

Therefore the product must not depend on an already-working VPN in order to install PrivatPirat.

## 5. Current prototype state to inspect before changes

Do not assume cleanup already happened.

On `PP-LAB-01`, the successful One-Tap prototype may still include:

- `/usr/local/bin/cloudflared`;
- `privatpirat-delivery.service`;
- `privatpirat-one-tap-tunnel.service`;
- localhost delivery on `127.0.0.1:18080`;
- `/etc/privatpirat-delivery/` with private subscription material and token;
- Cloudflare Quick Tunnel running over HTTP/2.

These are prototype delivery components only. They are not part of the accepted I/II/III route baseline. Inspect read-only first. Cleanup is a separate R3 change and must preserve I/II/III.

On the Android/Termux side, private client material exists under `~/deepwork-mobile/private/`, including client material for I, II and III and the generated triple subscription. Exact paths/values must not be copied into GitHub, Drive or chat beyond already-sanitized filenames where appropriate.

A local Termux HTTP preview on `127.0.0.1:18888` may also still be running from the HTML one-tap test. Treat this as local prototype residue, not infrastructure.

## 6. Important experimental lessons

- Polling commands that are expected to temporarily return no match must not terminate a script under `set -e` / `pipefail`.
- PASS must never be printed after an upstream failure.
- Administrative control paths must not depend on the exact route being restarted/tested.
- A synthetic connectivity probe is not authoritative unless it reproduces the real client behavior.
- Rollback must remove only the component introduced by the current gate.
- Bootstrap acceptance must be performed from the true zero-state: no pre-existing VPN dependency.
- Working subscription URLs, client URIs, UUIDs, REALITY material, Hysteria credentials, certificate pins, IP/hostname and raw configs/logs remain secret.

## 7. New architectural decision

Build a separate `PrivatPirat Bootstrap Gateway v0.1`.

The VPN origin node `PP-LAB-01` should remain the accepted VPN node and should not be repurposed as the public bootstrap identity.

The Bootstrap Gateway is a separate small VPS whose role is only to provide the initial private HTTPS subscription/bootstrap path. VPN user traffic should not transit this gateway after installation.

The user already has a second VPS available, but its current identity, provider details and technical state have not yet been safely inventoried in this workstream.

## 8. Bootstrap Gateway acceptance target

A PASS requires all of the following:

1. Start from an Android device with no working PrivatPirat/VPN path enabled.
2. One private installation link is reachable directly from the target Russian mobile/Wi-Fi network.
3. Happ imports exactly one `PrivatPirat AILab` subscription.
4. The subscription contains exactly I + II + III.
5. At least one imported route is then successfully connected and verified; preferably all three receive a short regression check.
6. Gateway uses ordinary trusted HTTPS on TCP/443.
7. The VPN origin node is not unnecessarily exposed through the gateway's public DNS/certificate metadata.
8. Gateway and PP-LAB-01 have independent lifecycle and rollback.
9. Operational secrets do not enter GitHub, Google Drive or chat.
10. The customer bootstrap flow does not require a pre-existing VPN.

## 9. First task in the new chat

**Do not build immediately.** First locate and inspect the second VPS safely.

Required sequence:

`identify second VPS -> verify host identity/access -> read-only inventory -> decide gateway architecture -> R3 change packet -> build -> zero-state Android acceptance -> evidence -> cleanup of obsolete Quick Tunnel prototype`

The first server action must be read-only. Do not install packages, change firewall/SSH, issue certificates, move client secrets or alter PP-LAB-01 until inventory and a new R3 packet are approved.

## 10. Model / execution mode

Use `Sol / High` for the Bootstrap Gateway architecture, server changes, security boundaries and final acceptance. Lower-cost modes may later be used for routine repetitive execution after the architecture and runbook are stable.

## 11. Product direction

PrivatPirat AILab is the applied/laboratory face under DeepWork AILab. Current product proposition:

> «Дай нам свой VPS — через несколько минут получи проверенный приватный трёхмаршрутный VPN-контур и одну ссылку для установки».

Core value: verifiable safety and honest acceptance criteria. A feature is not called secure or production-ready merely because it technically works in a favorable environment.

## 12. Immediate new-chat instruction

Start by reading this handoff, `AGENTS.md`, current README, experiment protocol, the One-Tap evidence checkpoint, and the DeepWork AIHub Integration Registry. Then help identify the user's second VPS without asking them to reveal passwords or private keys in chat. Perform a read-only inventory first and propose the minimal Bootstrap Gateway v0.1 architecture before any write.
