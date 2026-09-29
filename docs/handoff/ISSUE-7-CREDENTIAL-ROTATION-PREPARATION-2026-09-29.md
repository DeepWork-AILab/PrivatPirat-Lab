# Issue #7 — credential rotation preparation

**Date:** 2026-09-29
**Status:** DRAFT RUNBOOK / NOT EXECUTED
**Issue:** [historical PP-LAB-I credential](https://github.com/DeepWork-AILab/PrivatPirat-Lab/issues/7)

## Known and unknown

FACT — Issue #7 is open. It records a historical client connection credential in local PowerShell history. No remediation evidence is present in the issue at this review.

TODO — Privately establish whether that exact credential is still accepted, which route/recipient owns it, and which client/server surfaces use it. These mappings were not inspected here. Do not guess from an old filename or rotate unrelated identities.

## Preparation gate

1. Locate the affected history source locally without echoing its contents; identify coupled secret fields privately.
2. Inspect exact live target identity, authentication scope and dependencies read-only.
3. Confirm an independent administrative recovery path and a protected backup outside Git/Drive/chat.
4. Prepare the smallest configuration change, syntax validation, application path test and unaffected-recipient regression.
5. Present the exact private target/run and impact to the owner. This document is not execution authorization.

STOP on uncertain mapping, unexpected configuration, missing admin recovery or inability to test isolation. No executable command is provided because the live mapping is not yet established.

## Authorized run, once prepared

1. Create fresh replacement material through the target's supported mechanism without printing it into logs.
2. Update only the mapped server/client surfaces and distribute the replacement privately through the existing authorized workflow.
3. Prove the new identity on the accepted user data path, including clean reconnect; retain authenticated administrative access.
4. Revoke the exposed identity and any coupled material the actual configuration requires.
5. Prove that the old identity fails authentication in a fresh session. Cached connections do not establish revocation.
6. Recheck unaffected recipients/routes, and remove the cleartext history copy and known task-created copies without broad deletion of unrelated history.
7. Record only sanitized outcomes, dates, affected roles, verification method and remaining uncertainty.

## Recovery and closure

Preserving rollback means retaining recoverable service configuration and independent administration. It does not mean automatically re-enabling the exposed credential. If replacement validation fails, stop and choose a bounded safe recovery.

Close issue #7 only after new-credential PASS, old-credential authentication FAIL, unaffected-path PASS and local-copy remediation are all documented. Until then the issue stays open; the historical laboratory acceptance remains a separate result.
