# PP-LAB Builder Predeploy Checkpoint — 2026-08-30

## Status

- `FACT` — accepted baseline `PP-LAB-I + PP-LAB-II + PP-LAB-III` remains complete through G4 PASS.
- `FACT` — current Builder code is on `main` commit `a4f3cd69d3b17ae848cfc6bc4f1ec0757ec98389` (`builder: support passwordless sudo transport`).
- `FACT` — CODE-4 armed the reviewed `--apply` entrypoint without changing route logic.
- `FACT` — CODE-5 added privilege transport for either direct root or independently proven passwordless `sudo -n`.
- `FACT` — last local verification completed with 46 unit tests PASS, render check PASS and structural checks PASS.
- `FACT` — route render/build/rollback logic was held unchanged during CODE-5.
- `FACT` — clean-room target SSH identity was independently verified before deployment work.
- `FACT` — provider-issued SSH account is non-root, while passwordless sudo capability to UID 0 was independently confirmed.
- `FACT` — no clean-room deployment stage has started yet; no PP-LAB routes have been installed on the acceptance target.
- `FACT` — server write count for the clean-room target remains zero at this checkpoint.

## Decisions encoded in Builder

- `DECISION` — privilege is capability-based, not username-based: direct UID 0 is accepted; otherwise Builder requires `sudo -n` to obtain UID 0.
- `DECISION` — sudo password transport is forbidden; no `sudo -S`, `sshpass`, password-in-argv, password-in-env or password file is used.
- `DECISION` — privileged remote payloads execute through system OpenSSH and stdin-based shell transport.
- `DECISION` — root-owned material transfer avoids leaving private payloads in the ordinary remote user's home directory.
- `DECISION` — route I/II/III remain separate staged transactions with scoped rollback and mandatory regression.

## Failures discovered before deployment

These are process/tooling failures, not route failures:

1. An overly broad secret-pattern scan inspected the whole diff and matched forbidden token names inside negative tests that asserted those tokens were absent from executable code.
2. Two new tests used a hard-coded `/tmp` path that is not portable to Termux.
3. Python verification created `__pycache__` directories that were then misclassified as unexpected source-tree dirt.
4. Wrapper commands around the Builder created operator friction without adding deployment correctness.
5. Repeated manual handling of SSH fingerprint text conflicted with the smartphone-first objective.

Each stop happened before commit/deployment progression or before clean-room server writes.

## Corrective methods

- Check executable code and negative-test fixtures separately when scanning for forbidden runtime constructs.
- Protect critical route functions with structural or byte-identical invariants instead of fragile grep-only heuristics.
- Use `tempfile.TemporaryDirectory()` for portable tests.
- Ignore generated Python bytecode/cache artifacts and gate tracked source state explicitly.
- Perform one distinguishing read-only capability test before expanding implementation assumptions.
- Reduce operator shuttling: secrets and trust anchors should be entered or consumed locally, not repeatedly copied through chat.

## Security/publication note

This checkpoint intentionally omits working addresses, host-key values, login credentials, UUIDs, REALITY material, ports, SNI/target values, Hysteria credentials, client URIs and raw logs.

## Current verdict

`DECISION` — Builder implementation checkpoint: `PASS / READY FOR CLEAN-ROOM ACCEPTANCE`.

`TODO` — run one explicitly authorized clean-room Builder acceptance against the independently verified target and obtain `PASS`, `PARTIAL` or `FAIL` from the real I → II → III sequence.
