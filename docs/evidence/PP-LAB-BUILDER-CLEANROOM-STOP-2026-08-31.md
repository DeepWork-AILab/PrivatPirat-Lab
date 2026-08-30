# PP-LAB Builder — clean-room STOP checkpoint

**Evidence ID:** `PP-LAB-BUILDER-CLEANROOM-STOP-2026-08-31`  
**Local checkpoint date:** 2026-08-31  
**Verdict:** `STOP / NOT READY FOR ANOTHER LIVE ACCEPTANCE RUN`

## Scope

This checkpoint records the first real clean-room Builder work after the predeploy readiness checkpoint. It is intentionally sanitized: no target address, SSH identity, fingerprint, selected ports, cover hostname, route credentials, client URI, complete configuration or raw secret-bearing log is included.

## Confirmed execution facts

- The accepted manual PP-LAB I/II/III baseline remains unchanged at G2/G3/G4 PASS.
- The Builder reached the authorized clean-room target through pinned OpenSSH transport and proven passwordless privilege escalation.
- Local artifact acquisition and SHA-256 verification completed.
- Route I server configuration validation, systemd activation and listener health were observed during failed development runs.
- The Termux-local ephemeral Xray verifier did not establish the required Route I data path.
- No route reached Builder acceptance; Route II and Route III were never reached.
- Every reported failed Route I attempt ended with `ROLLBACK_I=PASS` or its equivalent scoped rollback marker.
- No client bundle was accepted and formal Wi-Fi/mobile/DNS acceptance was not run.

## Runtime defects exposed and corrected

1. Embedded Python in the I/II/III stage scripts rendered an unescaped newline inside a string literal and failed before writing route material.
2. Failed-stage rollback removed route-specific children but could leave empty Builder parent directories, causing the next clean-room preflight to stop.
3. The generated Xray verification profile used `SpiderX=/`, while the accepted working PP-LAB-I client baseline used empty `SpiderX`.
4. The ephemeral verifier stored Xray JSON under a `.conf` suffix instead of a parser-specific `.json` suffix; Hysteria verification now uses `.yaml`.

The corrections are present on GitHub `main` through:

- `dbe1bed4a4d07c6cdfecf42c1d27316161ab9457` — embedded stage Python newline correction and compile regression coverage;
- `c047d73fa7a652c7d47fcb7bad70a44c4ad542a0` — accepted Reality client alignment and empty rollback-parent cleanup;
- `ccf58e26de5cca2eef60f54f2efda236bab57ff8` — parser-specific verifier configuration suffixes.

Current non-live verification after these changes is 52 tests PASS, render check PASS and local prerequisite check PASS.

## Remaining blocker

The latest live run still ended at `ROUTE_I_DATA_PATH_FAIL=STOP`. Because that run did not retain sufficiently specific local client startup/probe output, the exact remaining Termux-local verifier cause is not established.

`DECISION` — do not run more blind VPS retries. Reproduce the verifier locally with the actual Android/Termux client binary, retain sanitized stdout/stderr, distinguish configuration parsing, SOCKS startup and HTTP/HTTPS/exit probes, and add the smallest regression coverage before another server gate.

## Target-state boundary

Rollback markers are evidence that the scoped cleanup command completed, but they are not a substitute for a fresh inventory.

`REQUIRED BEFORE NEXT WRITE` — one read-only target inventory must confirm absence of relevant Builder paths, users, units, listeners and other pre-existing route state.

## Authorization boundary

The prior one-run clean-room server gate ended with this STOP and is consumed. Local diagnosis and repository changes may continue. A new live server-write run requires a fresh explicit owner authorization after the remaining verifier blocker is locally isolated and tested.

## Current conclusion

`BUILDER_ACCEPTANCE=STOP`  
`ROUTES_ACCEPTED=NONE`  
`CLIENT_BUNDLE=NOT_READY`  
`FORMAL_MULTI_NETWORK_ACCEPTANCE=NOT_RUN`  
`NEXT_PHASE=LOCAL_VERIFIER_DIAGNOSIS`
