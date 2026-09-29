# Article backlog review

**Date:** 2026-09-29  
**Status:** `EDITORIAL REVIEW / SANITIZED`

## Review result

The existing article material is substantial and worth keeping. It is currently spread across narrative drafts, technical notes and project evidence. The main editorial problem is not lack of material; it is that different stories have different proof requirements while some notes use one shared publication gate.

Each article should have its own evidence gate. A delivery or diagnostic story does not need to wait for the Reproducible Node Builder to complete unless its thesis claims Builder reproducibility.

## Priority backlog

| Priority | Working subject | Current strength | Missing before publication | Recommended next form |
|---|---|---|---|---|
| 1 | The owner became the message bus between AIs | Strong lived narrative and repeated engineering examples | Tight chronology, two or three concrete scenes, date-stamped tool/model references, measured operator burden where available | Long-form essay |
| 2 | TLS error in Happ while the Hysteria2 path worked | Strong bounded technical incident with a useful diagnostic lesson | Final fact check against sanitized evidence; remove live connection details; state which root-cause claims remain unproven | Technical case study |
| 3 | One personal link as a product layer over three routes | Strong project arc, now supported by the 2026-09-29 owner report | A simple architecture illustration and a clear separation between owner report and formal route acceptance | Product-engineering article |
| 4 | Service active, request path dead | Compact and memorable proven failure mode | Minimal reproducible pseudocode or sanitized handler example | Short technical article |
| 5 | A server can work and still be the wrong server | Useful provider-suitability lesson | Exact dated observations, closure of any provider/account story, neutral wording that avoids a broader provider claim | Field report |
| 6 | APK “3/66” comparative audit | Interesting security-analysis material | Reproducible collection log, dynamic analysis or sandbox results, version hashes and an explicit uncertainty section | Hold for more evidence |

## Review of the strongest existing drafts

### “Я становился прослойкой между своими ИИ”

This is the strongest general-audience piece. Its central idea is durable: automation can increase the operator's attention cost when the human must copy commands, move results and repair context between control and execution systems.

The recent project history strengthens the article:

- repeated manual Termux and wrapper steps exposed the attention cost;
- bounded one-command flows showed what a better interface should feel like;
- STOP conditions remained valuable even when their operator UX was expensive;
- recovery records show how facts, decisions and uncertainty can survive handoffs.

Editorial correction: keep model and product names as dated examples rather than the thesis. The article should remain understandable if those tools change.

### TLS / Hysteria2 diagnostic story

This material is suitable for a focused technical case study. Its value is the discipline of separating:

- local client parsing and UX;
- TLS and certificate behavior;
- server service state;
- authenticated transport;
- actual end-to-end data path.

The article can be drafted before every later delivery milestone is complete, provided it is framed as a historical diagnostic episode and the evidence boundary is explicit.

### APK comparative audit

The static comparison is a useful start, but “3/66” is easy for readers to overinterpret. Publication should wait until the record includes exact sample identity, hashes, tool versions, collection date, repeatability and dynamic behavior. The final piece should explain what the count can and cannot establish.

## New article seeds supported by current evidence

### “Одна ссылка, три маршрута: почему VPN становится продуктом только на слое доставки”

Core thesis: the protocols can already work while onboarding remains fragile. Recipient identity, revoke/rotation, stable HTTPS delivery, metadata and a VPN-off installation path form a separate product layer.

Evidence boundary: use formal route evidence for the three transports and the 2026-09-29 owner report only for the current Landing and installation observation.

### “Сервер установлен, но не принят”

Core thesis: technical deployment is only one acceptance dimension. Required destinations, egress suitability, user tasks and provider behavior decide whether the node belongs in the active architecture.

### “Один read-only тест вместо пяти исправлений”

Core thesis: AI-assisted recovery improves when each unexpected result first triggers one distinguishing observation. This story can combine the client-schema incident, SSH capability detection and service-active/request-dead episode.

### “Почему причина может остаться неизвестной после успешного восстановления”

Core thesis: recovery and root-cause proof are separate outcomes. A system can return to service while the record honestly keeps causation unproven.

## Editorial structure to use for every article

1. reader problem;
2. concrete incident;
3. what was observed;
4. tempting but unsupported explanation;
5. distinguishing test;
6. bounded change or STOP decision;
7. user-facing verification;
8. remaining uncertainty;
9. reusable rule.

## Repository organization recommendation

- Keep raw and chronological project evidence in `docs/evidence/`.
- Keep reusable lessons and article seeds in `docs/field-notes/`.
- Maintain one backlog review like this as the editorial index.
- Put a full publication draft in its own file only after its individual evidence gate is met.
- Date any tool, model, provider or malware-scan result because these details age quickly.

## Immediate editorial order

1. outline and finish “Я становился прослойкой между своими ИИ”;
2. prepare the TLS/Hysteria2 technical case study;
3. draft “Одна ссылка, три маршрута” after adding one sanitized architecture figure;
4. preserve the APK article as research until dynamic and reproducibility evidence exists.

No live infrastructure values, recipient identities or deployable connection material belong in public article drafts.
