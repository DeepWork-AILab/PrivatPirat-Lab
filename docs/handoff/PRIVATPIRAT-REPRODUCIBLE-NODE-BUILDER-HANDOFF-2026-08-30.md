# PrivatPirat Reproducible Node Builder v0.1 — Handoff

**Checkpoint date:** 2026-08-30  
**Project:** DeepWork AIHub / PrivatPirat Lab  
**Canonical repo:** `DeepWork-AILab/PrivatPirat-Lab`  
**Branch:** `main`  
**Status:** Builder implementation ready; clean-room deployment not yet started

## 1. Read first

1. `AGENTS.md`
2. `README.md`
3. `docs/EXPERIMENT_PROTOCOL.md`
4. `docs/evidence/PP-LAB-BUILDER-PREDEPLOY-CHECKPOINT-2026-08-30.md`
5. accepted G2/G3/G4 evidence
6. current `scripts/pp-build.py`

Current GitHub `main` is authoritative over chat history.

## 2. Accepted baseline

`FACT` — original PP-LAB experiment is complete:

- I — VLESS / RAW(TCP) / REALITY / Vision — PASS.
- II — VLESS / XHTTP / REALITY — PASS.
- III — Hysteria2 / TLS / QUIC / UDP — PASS.

Builder must reproduce those three independently selectable routes on a clean Ubuntu target without manually configuring the target route-by-route.

## 3. Builder implementation checkpoint

`FACT` — current Builder commit at this handoff is `a4f3cd69d3b17ae848cfc6bc4f1ec0757ec98389`.

`FACT` — CODE-4 armed `--apply` to dispatch into the already reviewed deployment engine.

`FACT` — CODE-5 added capability-based privilege transport:

- direct remote UID 0 remains supported;
- a non-root SSH account is supported only if `sudo -n` independently proves effective UID 0;
- no sudo password is read, stored or transported;
- privileged stage/inventory commands use system OpenSSH;
- root-owned payloads use SSH stream transport instead of ordinary-user staging.

`FACT` — last local verification: 46 tests PASS, render check PASS, structural check PASS.

## 4. Clean-room target state

`FACT` — target SSH host identity has already been independently authenticated.

`FACT` — provider-issued SSH identity is non-root.

`FACT` — passwordless sudo capability to UID 0 has been independently observed.

`FACT` — no route deployment has started on the target and no Builder server write has occurred at this handoff.

Operational address, login data, host-key values and other sensitive target data are intentionally omitted.

## 5. Existing authorization

A prior server gate was approved for one clean-room target/run. Because CODE-5 changed privileged execution semantics, the run should proceed only under the final reviewed `sudo` change packet already agreed in the workstream. Do not reinterpret this handoff as general delegated authorization or permission for another target.

## 6. Immediate goal in the next chat

One task only:

> Run the existing Builder once against the clean-room target and drive the staged I → II → III acceptance to PASS or an honest STOP.

Do not create another parallel project. Do not manually configure routes on the VPS. Do not add helper scripts, wrapper layers or new code gates unless the Builder exposes a real blocker that can be demonstrated by one distinguishing read-only test.

## 7. Intended run

Conceptual flow:

`private target input → pinned host identity → privilege probe → clean-room inventory → I build/verify → II build/verify + I regression → III build/verify + I+II regression → client bundle → sanitized verdict`

Human actions should be limited to:

- local target/trust input;
- normal OpenSSH authentication;
- private REALITY cover input;
- physical Wi-Fi/mobile switching when requested;
- leak-oriented DNS checkpoint;
- explicit stop/decision if Builder reports unexpected state.

## 8. Important UX/process lessons

- Do not make the human shuttle operational data through chat when local consumption is possible.
- Capability must be smoke-tested before implementation assumes root, filesystem layout or platform behavior.
- Do not use hard-coded `/tmp` paths for Termux tests; use platform-safe temp APIs.
- Generated `__pycache__` is not a source change.
- A security scanner must distinguish executable code from negative test fixtures.
- Safety STOPs are valuable only if they reduce blast radius without creating avoidable operator burden.

Detailed lessons are recorded in `docs/field-notes/PP-LAB-BUILDER-PREDEPLOY-LESSONS-2026-08-30.md`.

## 9. Stop conditions

Stop before or during the run on:

- host identity mismatch;
- privilege capability mismatch;
- unsupported OS/architecture/resources;
- unknown/custom firewall or unexpected existing PrivatPirat state;
- occupied selected port;
- artifact/checksum/config validation failure;
- lost control path;
- route data-path failure;
- regression failure;
- DNS checkpoint failure/missing required target network;
- rollback failure;
- need for manual server repair outside Builder.

If manual server repair is required, Builder acceptance is FAIL until the correction is encoded and rerun from known state.

## 10. Next useful action

Start from the existing Builder, not from another round of architecture work. Keep the operator path minimal and let Builder itself reveal the next real blocker, if any.
