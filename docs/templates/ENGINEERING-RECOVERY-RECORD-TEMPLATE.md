# Engineering recovery record template

**Date:** `YYYY-MM-DD`  
**Status:** `DRAFT | ACTIVE INCIDENT | RECOVERED | STOP | CLOSED`  
**Affected component:** `<bounded component name>`  
**Operator:** `<role or sanitized identifier>`

## 1. Last accepted baseline

State the last proven working condition and link to its dated evidence.

- Baseline:
- Evidence:
- What this incident may affect:
- What remains outside scope:

## 2. User-visible symptom

Describe what the user or recipient actually observed.

- Network/client context:
- First observed time:
- Reproducibility:
- Exact boundary where the symptom appears:

Do not replace the symptom with a guessed cause.

## 3. Observations

Record facts with their source.

| Observation | Source | Time | Classification |
|---|---|---|---|
|  | owner report / client test / server read-only check / provider control plane |  | `FACT | OWNER REPORT` |

Keep service state, client UI state and end-to-end data-path evidence separate.

## 4. Failure classification

Choose the narrowest supported class.

- [ ] client schema or local parsing
- [ ] client UX or stale state
- [ ] DNS or certificate coverage
- [ ] transport or network path
- [ ] service process or request handler
- [ ] authentication or credential
- [ ] provider or egress suitability
- [ ] SSH identity or privilege boundary
- [ ] automation harness
- [ ] unknown

**Current classification:**  
**Confidence and reason:**

## 5. One distinguishing read-only test

- Competing explanations:
- Read-only test:
- Expected result for each explanation:
- Observed result:
- Decision:

If the result is unexpected, stop and update the record before proposing another change.

## 6. Bounded recovery action

- Exact target:
- Authorized change:
- Expected result:
- Verification:
- Backup:
- Rollback:
- Stop condition:

Do not combine unrelated repairs in one recovery gate.

## 7. Execution record

- Start time:
- End time:
- Commands or tool references, sanitized:
- Unexpected results:
- Rollback used:
- Secrets exposed: `NO | YES — rotate and open a security record`

Never paste working credentials, subscription URLs, private keys, complete configs or raw secret-bearing logs.

## 8. User-facing verification

Record proof at the layer where the failure was observed.

- Client and version:
- Network:
- DNS result:
- HTTP/HTTPS or application data path:
- Exit identity where applicable:
- Reconnect repetitions:
- Restart/reboot recovery where applicable:
- Isolation from unrelated routes or recipients:
- Result: `PASS | PARTIAL | FAIL | NOT RUN`

An active service or successful handshake is not a substitute for the relevant user-facing check.

## 9. Recovery verdict

**Operational state:** `RECOVERED | PARTIAL | FAILED | UNKNOWN`  
**Root cause:** `PROVEN | UNPROVEN`

- What is proven:
- What remains uncertain:
- Why progression may continue or must stop:

Recovery may be proven while root cause remains unproven.

## 10. Follow-up

- Credential rotation required:
- Documentation update:
- Issue or PR:
- Monitoring period:
- Owner:
- Closure condition:

## Public sanitization checklist

Before publishing:

- [ ] recipient and personal names removed;
- [ ] live URLs and hostnames removed;
- [ ] server addresses and ports removed;
- [ ] UUIDs, passwords, tokens and private keys removed;
- [ ] raw logs reduced to necessary observations;
- [ ] owner report distinguished from independent acceptance;
- [ ] historical PASS distinguished from current live state;
- [ ] root-cause uncertainty preserved.
