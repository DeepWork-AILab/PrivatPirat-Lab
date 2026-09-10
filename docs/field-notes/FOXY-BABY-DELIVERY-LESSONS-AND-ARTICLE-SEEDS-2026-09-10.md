# Foxy Baby — delivery lessons and article seeds

**Date:** 2026-09-10  
**Status:** `EDITORIAL / ENGINEERING FIELD NOTES`

## Why this note exists

Foxy Baby moved PrivatPirat Lab from a working three-route personal node toward a multi-recipient, persistent, human-facing delivery system. The useful part is not only what passed, but also the sequence of false starts, STOP decisions and client-side ambiguities that exposed where infrastructure proof ends and product UX begins.

This note is sanitized. It contains no working addresses, hostnames, ports, tunnel identifiers, UUIDs, SNI, recipient tokens, credentials, direct client links or raw configs.

## Engineering lesson 1 — multi-recipient means independent failure domains at the credential layer

A single shared client profile is easy to demo and hard to operate. Foxy Baby demonstrated a more useful product boundary:

- one owner-only identity;
- independent recipient identities;
- separate authentication material per route;
- separate subscription identity per recipient;
- revoke/rotation of one recipient without touching the others.

The important proof was not provisioning itself but rotation: old credentials stopped working, replacement credentials worked, and unrelated recipients remained unaffected.

### Article seed

**«Не раздавайте один VPN-профиль всем: как независимая ротация превращает лабораторный сервер в обслуживаемый продукт»**

## Engineering lesson 2 — persistence is not one systemd unit

The transient delivery prototype coupled each loopback origin with its Quick Tunnel process under the same supervisor/cgroup. That worked as a field experiment but was a poor persistence boundary.

The first migration attempt correctly stopped when this coupling was discovered. The eventual design separated:

- persistent landing origin;
- persistent subscription origin;
- persistent Named Tunnel connector.

Only after direct loopback verification were stable public routes switched to the new origins.

### Article seed

**«Почему “оно переживает reboot” — это не один флаг enabled: разделяем origin, tunnel и rollback boundary»**

## Engineering lesson 3 — service active can hide a dead request path

A newly persistent Python subscription origin started successfully and stayed `active`, yet every real request disconnected. The cause was a method name collision: a handler method named `headers` shadowed an instance attribute used by `BaseHTTPRequestHandler`.

This episode is a clean demonstration of the repository rule that service state is intermediate evidence, not data-path proof.

The smallest correction changed only the handler implementation and restarted only that new subscription-origin unit.

### Article seed

**«systemd говорит active, а HTTP мёртв: почему data-path тест сильнее статуса сервиса»**

## Engineering lesson 4 — certificate coverage is architecture, not cosmetics

A nested subscription hostname resolved correctly and pointed at the right tunnel, but edge TLS failed because the active certificate did not cover that hostname shape. A first-level sibling hostname on the same persistent tunnel solved the issue without touching routes or origins.

The lesson is to validate edge certificate coverage before treating DNS success as HTTPS readiness.

### Article seed

**«DNS PASS, Tunnel PASS, TLS FAIL: как wildcard/certificate coverage ломает правильную схему на последнем метре»**

## Engineering lesson 5 — client UX can lie about infrastructure state

Happ produced several misleading states during otherwise successful imports:

- a timeout message while the subscription had actually been added;
- a technical-hostname group title before a later refresh applied the intended profile metadata;
- later direct-key imports that worked cleanly.

This variability should not be turned into a server failure without an independent subscription/data-path check.

### Article seed

**«Клиент показал timeout, а подписка уже внутри: как не перепутать UX-state с network-state»**

## Engineering lesson 6 — direct delivery and beautiful Landing are different product layers

The direct Happ delivery keys work and expand into the expected three-profile subscription. The remaining imperfect part is the personal HTTPS Landing in a true VPN-off mobile zero state.

This distinction matters commercially: a polished bootstrap page is valuable, but it is not the same as the core technical capability to deploy and verify the three-route node.

### Article seed

**«Когда продукт уже можно продавать, хотя onboarding ещё не идеален»**

## Engineering lesson 7 — a zero-state test must actually be zero-state

An early mobile test became invalid because the VPN state changed while the client request was in progress. The corrected method had to be autonomous: prepare the command, switch VPN off, run the complete probe without returning to the chat, then reconnect only after the result was written locally.

This is a reusable test-harness lesson for smartphone-first work.

### Article seed

**«Как тестировать сеть со смартфона, если сам чат требует VPN: автономный probe вместо ручного метания между приложениями»**

## Engineering lesson 8 — protocol comparison narrowed the current bootstrap failure

On the tested VPN-off mobile path:

- HTTPS and HTTP status were reachable;
- the landing origin itself returned a complete body with correct Content-Length;
- a forced HTTP/1.1 request began receiving body bytes;
- a forced HTTP/2 request received headers but stalled at zero body bytes until timeout;
- Cloudflare control-plane review found no explanatory hostname-specific WAF/Worker/redirect/cache/origin-rule difference versus the working primary One-Tap pattern.

This does not yet prove whether the carrier path or edge behavior is causal. It does prove that rewriting the Landing HTML or VPN routes would be speculative at this point.

### Article seed

**«200 OK без body: как мы сузили “пустую страницу” до HTTP/2 transport boundary и не полезли чинить Python наугад»**

## Engineering lesson 9 — dashboard automation can be the failing component

A narrowly scoped Cloudflare response-body-buffering experiment was prepared, but two Browser Assistant attempts stopped before the setting availability check because Chrome/dashboard control timed out.

No rule was created. The correct conclusion is not “Cloudflare rejected the setting”; it is “the automation path failed before the product hypothesis was tested.”

### Article seed

**«Не путайте failure automation с failure infrastructure: почему два STOP не означают, что настройка невозможна»**

## Engineering lesson 10 — rollback-first migrations reduced risk

Useful repeated pattern across the session:

1. preserve the working path;
2. add the new component in parallel;
3. test the new component directly;
4. switch only the minimal routing layer;
5. keep rollback material until post-switch and post-reboot acceptance pass.

This was especially important for the transition from transient delivery to persistent origins and stable Named Tunnel routing.

## Product lesson — one recipient object, three transports

The user-facing object is no longer “three unrelated configs.” It is one recipient-specific subscription containing three independently selectable transport profiles. That is a more coherent product unit while preserving route independence underneath.

## Commercial lesson — do not let the lab consume the first sale

The core commercial skill is:

> clean VPS -> secure administration -> three independent transports -> verified client data path -> recovery/isolation checks -> deliverable client bundle.

Foxy Baby added stronger distribution and persistence proof, but perfect VPN-off Landing UX is not required before offering the underlying VPS setup service.

The next commercial-quality milestone is not another cosmetic Landing iteration; it is a successful timed clean-room Builder run that demonstrates how quickly the accepted baseline can be reproduced for a new customer.

## Suggested long-form article structure

### Working title

**«От трёх VPN-протоколов к раздаваемому продукту: что сломалось между systemd, Cloudflare, Android и Happ»**

### Chapters

1. Why three transports on one VPS are useful but not high availability.
2. From owner-only configs to independent recipients.
3. Rotation/revoke as the real multi-user acceptance test.
4. Quick Tunnel as prototype, Named Tunnel as persistent delivery.
5. Why origin/tunnel coupling complicated migration.
6. The `headers` collision: active service, dead HTTP.
7. TLS hostname coverage surprise.
8. Controlled reboot as persistence proof.
9. Happ timeout/hostname-first behavior and the difference between UI and data path.
10. Zero-state VPN-off Landing and the HTTP/1.1 vs HTTP/2 discriminator.
11. Why the lab stopped before speculative fixes.
12. What is already sellable and what Builder still has to prove.

## Editorial boundary

Before publication:

- sanitize all operational metadata again;
- avoid recipient/person names;
- do not include exact working hostnames, endpoints, ports, fingerprints, tokens or credentials;
- distinguish private mobile acceptance from formal Wi-Fi+mobile protocol acceptance;
- do not claim the unresolved HTTP/2 symptom has a known root cause until a future experiment proves it;
- update the article after the next clean-room Builder acceptance attempt with actual deployment timing and operator involvement.
