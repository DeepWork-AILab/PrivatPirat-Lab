# DeepWork AILab — Work Agent 01: LilFox Reproducible Builder

**Owner decision:** 2026-10-15  
**Status:** READY FOR FIRST WORK RUN (not deployed, not autonomously operating yet)  
**Goal:** build a reproducible, verifiable **single-VPS, three-transport** deployment workflow with minimal human relay work. This is the first practical agent-execution pilot of DeepWork AI Symbiosis.

## Why this exists

The VPN infrastructure is essential to the owner and their close contacts for access to online services. Preserve existing access. The human sets objectives, approves risk and performs unavoidable real-device checks; the agent performs the technical steps using directly connected tools, without asking the human to shuttle commands, logs or screenshots.

**Use ChatGPT Work as the task runner/coordinator** with existing GitHub, Google Drive and Desktop Commander access when available. OpenCode/OpenRouter and new paid services are **not requirements**. One agent may plan, inspect, implement and run deterministic tests. An independent model/reviewer is optional for high-impact changes; another model's agreement is never a substitute for real tests.

## Sources of truth, in order

1. Current GitHub `main`: [AGENTS.md](../AGENTS.md), [README.md](../README.md), [SECURITY.md](../SECURITY.md), [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md). These govern implementation, permissions and acceptance.
2. The actual read-only state of the selected local environment and target, when safely verified.
3. Google Drive [START_HERE.md](https://drive.google.com/file/d/1862EbHVUPJXmHY2A7ULEkv0eWdUuWoF3/view) and [LILFOX_AM_FULL_HANDOFF_2026-10-06.md](https://drive.google.com/file/d/1OcMnrDkntjZb5RKTz2QnXDtcSx_n7939/view), **latest section 20, including 20.37**. Section 19 documents the original Builder goal and **historical** owner acceptance (6 × 3 = 18/18); it does not certify the current Amsterdam state.
4. Historical notes only for resolving specific discrepancies. Avoid full-archive rereads.

Conflicting historical scopes: on Oct 14 a separate incident thread narrowed the **immediate Amsterdam repair** to one AmneziaWG personal connection. On Oct 15 the owner separately restored the **engineering priority** of finishing autonomous **three-route LilFox Builder**. Do not treat this document as authorization to change Amsterdam or to abandon a live-user incident. Keep these workstreams distinct.

## Existing verified starting point

- Connected Windows workstation `DESKTOP-80AR3EL` was online via Desktop Commander on Oct 15; availability must be rechecked on each Work run.
- Local checkout: `D:\Codex\PrivatPirat-Lab`; existing feature branch `codex/lilfox-am`, locally based on `1013f6c` on the observed date.
- Local tree has **uncommitted modifications** to `scripts/pp-build.py` and `tests/test_pp_build.py`, plus **untracked** `scripts/lilfox-family-bundle.py`, `tests/test_lilfox_family_bundle.py`, `web/`. Preserve all. Do not reset, clean, overwrite, merge or rebase as part of an initial inspection.
- On 2026-10-15, `python3 -B -m unittest discover -s tests -p test_*.py -q` from WSL at `/mnt/d/Codex/PrivatPirat-Lab`: **99 tests OK**, `RENDER_CHECK=PASS`. Native Windows Python test results differ owing at least partly to POSIX-mode assumptions; use the specified Linux/WSL test environment unless testing Windows behavior intentionally. This verifies code tests, **not VPN connectivity**.
- Three existing ExtraVM targets were reported: one working New Jersey, another New Jersey requiring recovery, and Amsterdam with incident. Live state must be rechecked before operational claims. The working New Jersey must remain intact.

## Transport contract

One clean Ubuntu 24.04 VPS, three independently configured/tested routes:
- **I:** VLESS TCP REALITY / Vision
- **II:** VLESS XHTTP REALITY
- **III:** Hysteria2 TLS / QUIC

Build I → verify → build II → verify plus I regression → build III → verify plus I/II regression. On a stage failure, stop and use the defined rollback. Never call a service `active` or config syntax `PASS` a verified client data-path `PASS`. A fresh-system proof must not require manual server corrections outside the Builder.

## First Work session — authorized scope

**Read-only assessment and plan first**, not a live deploy. In one run:

1. Recheck GitHub/Drive canons and Desktop Commander connection; run a minimal safe capability smoke test.
2. Inspect local feature-tree status and diff without altering files. Distinguish actual changes from line-ending noise. Inventory existing Builder, family delivery script, relevant tests, and outstanding manual fixes from the handoff.
3. Reproduce relevant WSL tests in non-writing mode and report exact commands, exit codes, and failures. Do not produce/log private credentials.
4. Produce a **single bounded change packet** for code-only closure: concrete file scope, acceptance tests, expected result, risks, rollback, and STOP triggers. Identify which work can be performed independently and which requires owner approval. Avoid new abstractions, services and tools unless a demonstrated blocker demands them.
5. Ask the owner for **one consolidated permission** for the scoped code changes. After approval, do the code work directly through connected tools, test it, review the diff and report objective results; do not request repeated manual command transfers.

## Permission boundaries

- **Never** change live VPS, active VPN, SSH trust/keys, DNS, firewalls, subscriptions, Caddy, user access, payment/billing, or remote automation without a distinct, target-specific owner approval and backup/rollback plan.
- No new VPS purchases, subscriptions, API fees or OpenRouter/OpenCode installation.
- No merge/push to main, production publish, secrets exposure or destruction of any uncommitted work. Follow the current AGENTS.md security/branch rules.
- The first live clean-room deploy, when authorized later, is a separate change packet/run. A real Android/Happ mobile acceptance is a distinct owner or trustworthy client-side verification gate.

## Anti-drift / watchdog contract

- Recheck the end goal before each substantial new phase: does the next action directly improve reproducible three-route deployment or objective verification?
- Set a concrete hypothesis and discriminating check before diagnosis. Do not repeat equivalent unsuccessful checks. After at most two materially different unproductive attempts, stop, summarize evidence and reassess rather than entering a testing loop.
- Prefer deterministic tests over model-to-model affirmation. Independent reviewer/model only for specific high-risk design or security questions, not a compulsory multi-agent chain.
- Stop on uncertain target identity, permissions, lost management path, unexpected existing state, possible secret disclosure, irreversible change, absent rollback or a contradiction with the canonical docs.
- Summarize with `FACT / HYPOTHESIS / DECISION / TODO`, **PASS / FAIL / NOT TESTED**, and **one next useful action**. Do not label a plan or a passing unit test as a functioning deployed VPN.

## Definition of Done

**This first Work run is DONE** when the verified local state, engineering gaps, focused test outcomes, and one actionable owner-approval change packet are presented, without altering live infrastructure or losing local modifications.

**The long-term Builder goal is DONE only** after the owner has separately authorized a fresh-target live run and reproducible three-route server and real-device end-to-end acceptance passes with verifiable evidence. This document alone grants no such authorization.
