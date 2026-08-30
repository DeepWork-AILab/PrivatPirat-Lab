# PrivatPirat Reproducible Node Builder v0.1 — Handoff

**Checkpoint date:** 2026-08-30  
**Project:** DeepWork AILab / PrivatPirat Lab  
**Canonical repo:** `DeepWork-AILab/PrivatPirat-Lab`  
**Branch:** `main`  
**Status:** Clean-room acceptance `STOP`; Builder runtime integration debugging required; no route accepted

## 1. Read first

1. `AGENTS.md`
2. `README.md`
3. `docs/EXPERIMENT_PROTOCOL.md`
4. `docs/evidence/PP-LAB-BUILDER-PREDEPLOY-CHECKPOINT-2026-08-30.md`
5. `docs/evidence/PP-LAB-BUILDER-CLEANROOM-STOP-2026-08-31.md`
6. accepted G2/G3/G4 evidence
7. current `scripts/pp-build.py`

Current GitHub `main` is authoritative over chat history.

## 2. Accepted baseline

`FACT` — original PP-LAB experiment is complete:

- I — VLESS / RAW(TCP) / REALITY / Vision — PASS.
- II — VLESS / XHTTP / REALITY — PASS.
- III — Hysteria2 / TLS / QUIC / UDP — PASS.

Builder must reproduce those three independently selectable routes on a clean Ubuntu target without manually configuring the target route-by-route.

## 3. Builder implementation checkpoint

`FACT` — current GitHub `main` commit at this handoff is `ccf58e26de5cca2eef60f54f2efda236bab57ff8`.

`FACT` — CODE-4 armed `--apply` to dispatch into the already reviewed deployment engine.

`FACT` — CODE-5 added capability-based privilege transport:

- direct remote UID 0 remains supported;
- a non-root SSH account is supported only if `sudo -n` independently proves effective UID 0;
- no sudo password is read, stored or transported;
- privileged stage/inventory commands use system OpenSSH;
- root-owned payloads use SSH stream transport instead of ordinary-user staging.

`FACT` — verification before CODE-6: 46 tests PASS, render check PASS, structural check PASS.

`DECISION / CODE-6` — после доказанного operator blocker разрешены owner-approved CLI metadata (`target host`, SSH login/port, public host-key fingerprint) и явный одноразовый `--trust-current-host-key` для случая недоступной независимой provider console. TOFU закрепляет текущий ED25519 key, но не выдаётся за независимую identity verification. Passwords, private keys и route secrets по-прежнему запрещены в CLI. Controlled Builder STOP codes больше не должны скрываться как generic token redaction.

`FACT` — CODE-6 local verification: 49 tests PASS, local prerequisite check PASS, render check PASS; семь критических route render/apply functions сохранили исходные SHA-256 invariants.

`FACT` — clean-room execution exposed three runtime defects that predeploy unit/render checks had not covered:

- embedded Python newline escaping in I/II/III stage scripts;
- incomplete rollback of empty Builder parent directories and a client profile differing from the accepted empty-`SpiderX` baseline;
- parser-incompatible `.conf` suffix for ephemeral Xray JSON verification files.

`FACT` — these defects were corrected on `main` through commits `dbe1bed4a4d07c6cdfecf42c1d27316161ab9457`, `c047d73fa7a652c7d47fcb7bad70a44c4ad542a0` and `ccf58e26de5cca2eef60f54f2efda236bab57ff8`.

`FACT` — current local verification after those corrections: 52 tests PASS, local prerequisite check PASS and render check PASS. This is not an end-to-end Builder acceptance PASS.

## 4. Clean-room target state

`FACT` — ранее сохранённый ожидаемый fingerprint не совпал с ключом, предъявленным во время первого запуска Builder; Builder остановился до SSH authentication и server writes.

`DECISION` — независимая provider console недоступна; владелец отдельно разрешил CODE-6 и одноразовый TOFU для текущего clean-room run. После первого закрепления любое последующее изменение ключа остаётся STOP condition.

`FACT` — provider-issued SSH identity is non-root.

`FACT` — passwordless sudo capability to UID 0 has been independently observed.

`FACT` — multiple failed development runs reached Route I. The server configuration test, systemd service and listener reached healthy state, but the Termux-local client verifier did not establish the required data path.

`FACT` — every observed failed Route I run reported scoped rollback PASS. No route reached acceptance, no client bundle is ready and formal multi-network acceptance was not run.

`STOP CONDITION` — do not claim the target is clean from rollback markers alone. Before any future server write, perform exactly one read-only inventory confirming the absence of Builder paths, users, units, listeners and other relevant state.

Operational address, login data, host-key values and other sensitive target data are intentionally omitted.

## 5. Existing authorization

The previously approved one-run server gate ended in an honest clean-room `STOP`. It is consumed. Local/offline diagnosis and repository fixes may continue, but a new server-write acceptance run requires a fresh explicit owner authorization after the local verifier blocker is isolated and tested. Do not reinterpret this handoff as general delegated authorization or permission for another target.

## 6. Immediate goal in the next chat

One task only, in two strictly separated phases:

> First, reproduce and isolate the remaining Termux-local Xray verifier failure without VPS writes, add the smallest regression coverage, and restore `READY FOR CLEAN-ROOM ACCEPTANCE`. Only then request a fresh server gate and run one clean-room I → II → III acceptance to PASS or an honest STOP.

Do not create another parallel project. Do not manually configure routes on the VPS. Do not replay the prior inline deployment wrappers. Do not add helper scripts, wrapper layers or new code gates unless a remaining blocker is demonstrated by one distinguishing local test.

## 7. Intended run

Conceptual flow:

`owner-approved target metadata → verified fingerprint or explicit TOFU pin → privilege probe → clean-room inventory → I build/verify → II build/verify + I regression → III build/verify + I+II regression → client bundle → sanitized verdict`

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

Do not perform another live Builder run yet. Start with the actual Android/Termux client binary and a generated local verification fixture, capture its real startup output, and prove that the ephemeral verifier can open SOCKS and parse its route-specific configuration without using the VPS. After that proof and regression coverage, request a fresh server gate for one clean-room run.
