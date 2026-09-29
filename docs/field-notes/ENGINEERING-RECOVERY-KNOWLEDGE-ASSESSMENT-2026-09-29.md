# Engineering recovery knowledge assessment

**Date:** 2026-09-29  
**Status:** `FIELD NOTE / KNOWLEDGE DESIGN`

## Finding

FACT — No separate production bot named “engineering recovery bot” was identified in the sources reviewed here. This is a bounded search result, not proof that no such bot exists. It does not authorize building a replacement or a new autonomous executor.

FACT — Existing records contain useful recovery practice. Link those records from the existing knowledge base before duplicating them. TODO — If the owner means a specific bot or notebook, resolve its exact identity before editing that system.

## Traceable source map

| Reusable lesson | Source | Evidence boundary |
|---|---|---|
| Active service can have a dead request handler; certificate coverage can fail after DNS succeeds | [Foxy lessons 3–4](FOXY-BABY-DELIVERY-LESSONS-AND-ARTICLE-SEEDS-2026-09-10.md) | Historical incidents, not current faults |
| Independent recipient rotation and scoped rollback | [Foxy delivery checkpoint](../evidence/FOXY-BABY-RECIPIENT-DELIVERY-CHECKPOINT-2026-09-10.md) | Does not prove issue #7 remediated |
| Verifier failure and STOP after scoped rollback | [Builder STOP](../evidence/PP-LAB-BUILDER-CLEANROOM-STOP-2026-08-31.md) | Exact remaining client-verifier cause unproven |
| Client message versus actual routed application traffic | [Foxy closure source review](../evidence/FOXY-BABY-DIRECT-DELIVERY-SOURCE-REVIEW-2026-09-29.md) | No new live test; Termux was outside the tested route policy |
| Current recipient-facing result | [PP-LAB-01 owner report](../evidence/PP-LAB-01-RECIPIENT-DELIVERY-OWNER-REPORT-2026-09-29.md) | Owner report, not independent formal replay |

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

TODO — Use the [existing template in this draft](../templates/ENGINEERING-RECOVERY-RECORD-TEMPLATE.md) for the next actual incident. A read-only triage assistant is an optional proposal, not a new committed project. Keep execution in the existing bounded workflow.

## Editorial value

The recovery material supports several strong articles:

- why service health is weaker evidence than the user data path;
- how to distinguish client failure, transport failure and provider suitability;
- why one read-only test can prevent a chain of speculative repairs;
- how rollback boundaries make AI-assisted infrastructure work safer;
- why operator attention belongs in engineering acceptance criteria.

This note contains no working server metadata, credentials, recipient identities or deployable connection material.
