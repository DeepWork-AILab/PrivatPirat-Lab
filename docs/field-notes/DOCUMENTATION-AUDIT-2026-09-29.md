# Documentation audit

**Date:** 2026-09-29
**Status:** REVIEW / OPEN ITEMS EXPLICIT

| Classification | Finding | Treatment |
|---|---|---|
| FACT | README's Foxy front-door status stopped at the earlier partial checkpoint | Add sanitized review of the private later closure; preserve historical source |
| FACT | Earlier editorial review relaxed source holds | Restore the holds and the stated first-case policy |
| FACT | Recovery-bot identity was not established | Bound the finding to searched sources; link existing recovery records |
| FACT | Issue #7 remains open | Prepare a runbook; no claim of rotation |
| FACT | AGENTS.md prohibits adding a subscription endpoint while later accepted delivery evidence describes one | Instruction-scope conflict remains open; historical evidence does not authorize new writes |
| TODO | Clarify whether that AGENTS restriction applies only to the original route baseline | Requires an explicit owner decision and a reviewed instruction change; AGENTS.md is not weakened by this audit |

The last conflict matters for a new assistant: it must not infer permission to create or change delivery infrastructure merely from an existing operational checkpoint.

FACT — This is a documentation review. No VPS, DNS, client, subscription, credential, billing or live data-path test was performed. No clean-room Builder PASS, complete Foxy formal Wi-Fi acceptance, or project merger is claimed.
