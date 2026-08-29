# PrivatPirat Reproducible Node Builder v0.1 — Handoff

**Checkpoint date:** 2026-08-29  
**Project:** DeepWork AIHub / PrivatPirat AILab / PrivatPirat Lab  
**Status:** ready to continue in a new project chat  
**Next workstream:** `PrivatPirat Reproducible Node Builder v0.1`

## 1. Why this handoff exists

The original PrivatPirat Lab experiment is complete through G4 / PP-LAB-III = PASS. The current product priority is now reproducibility: build a second equivalent three-route node on a clean VPS without manually repeating the original setup.

The previously explored One-Tap / Bootstrap Gateway workstream is intentionally deferred. It remains documented separately and can be resumed later.

## 2. Canonical sources

1. GitHub source of truth: `DeepWork-AILab/PrivatPirat-Lab`, branch `main`.
2. Repository `AGENTS.md` — mandatory for all server work.
3. `README.md`.
4. `docs/EXPERIMENT_PROTOCOL.md`.
5. `docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md`.
6. `docs/evidence/PP-LAB-II-G3-PASS-2026-08-29.md`.
7. `docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md`.
8. `docs/evidence/PP-LAB-ONE-TAP-PROTOTYPE-v0.1-2026-08-29.md` for later product work only.
9. DeepWork AIHub canonical architecture: Google Doc `DeepWork AIHub — Integration Registry v0.2`.

If chat memory conflicts with current canonical documents, the documents win.

## 3. Accepted baseline to reproduce

The target node must reproduce the accepted three independently selectable routes:

- Route I — VLESS / TCP / REALITY / Vision.
- Route II — VLESS / XHTTP / REALITY.
- Route III — Hysteria2 / TLS / QUIC / UDP.

Each route uses its own port, service/unit and fresh credentials. Existing secrets from PP-LAB-01 are never reused.

## 4. New primary goal

Build `PrivatPirat Reproducible Node Builder v0.1` so that the human provides only:

- new VPS connection details;
- desired visible naming prefix / node name for generated client profiles;
- explicit R3 approval for the deployment run.

Then one Builder invocation should autonomously:

`inventory -> build I -> verify I -> build II -> verify II + regression I -> build III -> verify III + regression I+II -> collect client profiles -> final sanitized report`

The user should not manually configure the server route-by-route.

## 5. Product acceptance target

Primary acceptance formula:

> `Clean Ubuntu VPS + one Builder invocation -> verified PrivatPirat I + II + III -> three ready client profiles -> no manual server configuration.`

The second VPS must be the first clean-room acceptance target for the Builder. Do not manually configure the second VPS first and automate later. If a manual server fix is required outside the Builder, treat that as Builder FAIL, encode the correction in the Builder and rerun from a known state.

## 6. Runtime architecture

Preferred production runtime: **Python + system OpenSSH**.

Reasoning:

- works in Termux on Android;
- works on Windows / WSL;
- no dependency on a particular AI CLI;
- easier structured state/error handling than a large shell-only installer;
- supports deterministic verification, resumability, secret-safe file handling and scoped rollback.

AI tools such as ChatGPT, Codex, Claude Code or OpenCode may help design, review and test the Builder, but the production deployment must not depend on an AI model being present.

## 7. Smartphone-first requirement

`DECISION / TARGET`: the complete Builder workflow should be operable from the smartphone through Termux.

The intended mobile path is:

`ChatGPT/Work -> Termux -> Python Builder -> OpenSSH -> new VPS -> local private output -> client acceptance on the same Android device`

The smartphone should be sufficient for:

- entering the target VPS address / SSH identity locally;
- launching the one-command Builder;
- SSH transport and file transfer;
- generating/storing private client material locally;
- receiving sanitized progress and evidence;
- importing/testing the generated client profiles on Android.

Windows may remain a secondary development/heavy-debug endpoint, but must not be required for normal node deployment if the Termux path passes acceptance.

## 8. Possible USP — record for product strategy

**POSSIBLE USP:**

> «Клиенту не нужен AI: он получает стабильный, проверяемый инструмент, который из чистого VPS воспроизводимо собирает полноценный PrivatPirat-контур».

Associated product meaning:

- AI is used internally to design, audit and improve the system;
- the customer-facing result is deterministic infrastructure automation, not an AI-dependent service;
- customer value is reproducibility, verifiability and low operator effort;
- this supports the broader PrivatPirat AILab principle of honest, evidence-backed security claims.

This is a candidate USP, not yet a final marketing claim.

## 9. Builder requirements

The Builder should eventually provide:

- read-only preflight before writes;
- exact OS/architecture/resource checks;
- SSH host identity verification;
- free-port selection with collision checks;
- pinned upstream versions/checksums for Xray and Hysteria2;
- fresh per-node secrets generated without printing them to stdout/stderr;
- independent service/config boundaries for I, II and III;
- config validation before service start;
- staged verification after each route;
- regression of previously accepted routes after each new route;
- scoped rollback of only the current failed stage;
- resumable/idempotent behavior where safe;
- no false PASS after upstream failure;
- robust polling that does not die on expected temporary no-match results;
- client output files stored locally with restrictive permissions;
- sanitized evidence suitable for GitHub;
- no working IP/hostname, UUID, REALITY material, Hysteria credential, URI, certificate pin or raw config in public artifacts.

## 10. Human interaction target

Ideal deployment UX:

```text
pp-build
Target VPS: [local/private input]
SSH access: [existing local key / protected input]
Profile name: <user chosen name>

-> PRECHECK PASS
-> I PASS
-> II PASS
-> III PASS
-> REGRESSION PASS
-> CLIENT BUNDLE READY
-> FINAL VERDICT PASS
```

The human should not copy/paste dozens of commands or shuttle logs between tools.

## 11. Governance / R3 boundary

`AGENTS.md` currently describes the original single-server experiment and sequential route gates. The new Builder work must not silently bypass those rules.

Before first deployment write, explicitly adapt the project governance for reproducible multi-node deployment while preserving the same safety model:

- one human Builder invocation may contain multiple internal stages;
- internally, each route remains a separate transaction/gate;
- failure of a stage stops progression;
- rollback is scoped to the current stage;
- previously accepted routes must remain untouched except for defined regression checks.

Any required `AGENTS.md` amendment is itself a separate repository write and should be reviewed before deployment.

## 12. First task in the new chat

Do not configure the second VPS manually.

Start by:

1. reading this handoff and the canonical sources;
2. inspecting the existing repository for reusable artifacts and gaps;
3. designing the minimal Builder v0.1 structure and state model;
4. deciding the smallest safe `AGENTS.md` amendment needed for multi-node reproducibility;
5. preparing a secret-free read-only inventory path for the second VPS;
6. only after explicit R3 approval, use the second VPS as the clean-room Builder acceptance run.

## 13. Model / mode

Use `Sol / High` for Builder architecture, security boundaries, repository governance changes and the first clean-room deployment. Lower-cost modes may later handle repetitive implementation work once the architecture and tests are stable.
