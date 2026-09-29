# Engineering recovery knowledge assessment

**Date:** 2026-09-29  
**Status:** `FIELD NOTE / KNOWLEDGE DESIGN`

## Finding

The repository and the connected project notes do not identify a separate production bot named “engineering recovery bot.” They do contain enough proven recovery practice to form a useful recovery knowledge base.

The material is ready to be recorded as procedures and decision rules. It is not yet sufficient evidence for an autonomous bot with infrastructure write access.

## Recovery knowledge already demonstrated

### 1. Preserve the accepted baseline

A failed experiment should not silently rewrite or degrade a previously accepted route. Builder failures and later delivery work were kept separate from the accepted `PP-LAB-I/II/III` baseline.

Useful rule:

> Name the accepted baseline before changing anything, and state which part of it the proposed action may affect.

### 2. Classify the failure before choosing a repair

The project has encountered materially different failure classes:

- local client-schema failure;
- client UX state inconsistent with actual subscription state;
- TLS certificate coverage failure;
- service active while its request path was broken;
- transport or mobile-path instability;
- provider-egress suitability failure;
- SSH capability and privilege-boundary mismatch;
- automation harness failure without server failure.

Useful rule:

> Record the observed symptom, the nearest proven boundary and one read-only test that distinguishes the leading explanations.

### 3. Prefer bounded recovery

Successful recovery work changed the smallest justified component: a handler, a hostname shape, an origin process, a credential set or an automation precondition. Each bounded change had its own verification and rollback boundary.

Useful rule:

> A recovery action must state the exact component, expected result, verification, rollback and stop condition.

### 4. Separate infrastructure state from user data path

Repeated incidents showed that `active`, “connected,” successful DNS or a tunnel control-plane state can coexist with a broken user request path.

Useful rule:

> Recovery is complete only when the relevant user-facing path is tested at the layer where the failure was observed.

### 5. Treat provider suitability as an acceptance property

A temporary secondary node could be technically deployed while still being unsuitable for the intended service access. Successful protocol installation alone did not make that node a useful product path.

Useful rule:

> Test required destinations and user tasks before promoting a provider or egress path into the active architecture.

### 6. Record uncertainty without inventing a root cause

Earlier mobile and Landing anomalies did not always produce a uniquely proven cause. The project preserved observations and bounded hypotheses without converting sequence into causation.

Useful rule:

> If a recovery succeeded after several things changed, record the recovery point and keep the root cause `UNPROVEN`.

## Minimum record for each recovery episode

A durable recovery entry should contain:

1. date and affected component;
2. last accepted baseline;
3. user-visible symptom;
4. observations and their sources;
5. failure classification;
6. read-only distinguishing test;
7. smallest authorized change;
8. verification at the user-facing layer;
9. rollback result or rollback readiness;
10. remaining uncertainty;
11. secrets and personal data removed from the public record.

## What could be automated now

A bounded assistant could safely help with:

- creating the recovery record from operator notes;
- checking that required fields are present;
- separating facts, hypotheses, decisions and TODOs;
- locating the relevant acceptance evidence;
- proposing read-only distinguishing checks;
- warning when a proposed conclusion exceeds the evidence;
- preparing a reviewable runbook or draft change.

## What needs more design before autonomous execution

Infrastructure writes need an explicit access model, approval boundary, credential handling design, audit trail and tested rollback. The current evidence does not justify a general recovery bot that independently selects and runs server changes.

A practical next artifact would be a structured recovery template and a read-only triage assistant. Execution can remain in the existing bounded operator workflow until repeated incidents establish stable, testable playbooks.

## Editorial value

The recovery material supports several strong articles:

- why service health is weaker evidence than the user data path;
- how to distinguish client failure, transport failure and provider suitability;
- why one read-only test can prevent a chain of speculative repairs;
- how rollback boundaries make AI-assisted infrastructure work safer;
- why operator attention belongs in engineering acceptance criteria.

This note contains no working server metadata, credentials, recipient identities or deployable connection material.
