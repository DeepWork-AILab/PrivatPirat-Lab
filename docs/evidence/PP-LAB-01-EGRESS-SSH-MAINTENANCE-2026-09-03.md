# PP-LAB-01 — egress / WARP / SSH maintenance checkpoint

**Date:** 2026-09-03 (late evening, MSK)  
**Status:** `MAINTENANCE CHECKPOINT / PASS`  
**Scope:** existing accepted node `PP-LAB-01`; no route redesign; no VPS reboot.

## Purpose

Зафиксировать фактическое состояние узла после восстановления доступа к identity-sensitive web services через дополнительный IPv6 egress, проверить отсутствие побочного ущерба для принятых маршрутов и Amnezia, а затем закрыть обнаруженный небезопасный password-based root SSH access.

Эта запись не заменяет G2/G3/G4 acceptance и не объявляет новый route gate.

## Evidence boundary

- Сырые diagnostics, firewall dumps, journal excerpts и рабочие конфиги остаются вне Git.
- Working IP/hostname, client identifiers, VPN credentials, private keys, WARP private key, working URIs и REALITY/Hysteria secrets здесь не публикуются.
- Наблюдения ниже санитизированы до минимально необходимого операционного факта.

## Pre-change read-only inventory

- `FACT` — действующий сервер остаётся Ubuntu 24.04 LTS / x86_64.
- `FACT` — IPv4 egress остаётся прямым через provider uplink; Cloudflare trace показывал WARP off для IPv4.
- `FACT` — IPv6 egress идёт через отдельный WireGuard interface `warp`; Cloudflare trace показывал WARP on для IPv6.
- `FACT` — WARP peer настроен с `AllowedIPs = ::/0`; глобальный `0.0.0.0/0` не включён.
- `FACT` — policy routing сохраняет provider IPv4 path для собственного server IPv4 и локальных Docker/private ranges.
- `FACT` — `wg-quick@warp` был `active` и `enabled`; конфигурация поднимает IPv6 route и keepalive helper.
- `FACT` — DNS на WARP interface имеет default-route scope; IPv4 provider interface сохраняет собственные public resolvers.

## Route and service regression

- `FACT` — `PP-LAB-I` фактически обслуживается текущим `xray.service` и принимал живой client traffic во время диагностики.
- `FACT` — `xray@pp-lab-i.service` существует как старый template instance, но является `inactive/disabled`; его состояние не означает отказ `PP-LAB-I`.
- `FACT` — `PP-LAB-II` работает через `xray@pp-lab-ii.service` и был `active/enabled`.
- `FACT` — `PP-LAB-III` работает через отдельный `pp-lab-iii.service` и был `active/enabled`.
- `FACT` — Docker оставался active; контейнер AmneziaWG оставался `Up`.
- `FACT` — systemd failed units: `0` на финальной проверке.
- `FACT` — ранее неопознанный local-only Python listener идентифицирован как `privatpirat-delivery.service`.
- `FACT` — ранее неопознанный local-only `cloudflared` listener идентифицирован как `privatpirat-one-tap-tunnel.service`.
- `FACT` — ранее неопознанный UDP listener доказан как WireGuard listen socket интерфейса WARP.

## Web-service diagnostic interpretation

- `FACT` — bare `curl` к ChatGPT вернул WAF-style HTTP 403 как по IPv4, так и по IPv6/WARP.
- `FACT` — Google Accounts вернул HTTP 200 по обоим address families.
- `DECISION` — bare `curl` к ChatGPT не считать acceptance proof: результат не различает egress reputation от browser/session/WAF client checks.
- `FACT` — по операторскому наблюдению нормальный browser/app access к ChatGPT и Google sign-in восстановился после включения IPv6 WARP.
- `DECISION` — этот пользовательский access result фиксируется как operational observation, а не как новый formal route acceptance.

## SSH finding

До maintenance:

- `FACT` — effective sshd configuration допускала `PermitRootLogin yes`, `PasswordAuthentication yes` и public-key authentication.
- `FACT` — публичный SSH endpoint регулярно получал автоматические password-guess attempts для `root` и несуществующих usernames.
- `FACT` — passphrase-protected ED25519 identity для POCO/Termux присутствовала в `authorized_keys` с корректными ownership/mode.
- `FACT` — server debug подтверждал, что этот public key принимается сервером.
- `FACT` — первая key-only automation попытка завершилась FAIL без server writes: client использовал `BatchMode=yes`, поэтому не мог запросить passphrase для расшифровки private key.
- `FACT` — это был client-side authentication workflow defect, а не отказ authorized key, permissions или sshd policy.

## Applied maintenance

Перед изменением был создан server-side rollback backup текущей SSH-конфигурации. Raw backup остаётся вне Git.

Применён минимальный SSH hardening:

- `PubkeyAuthentication yes`;
- `PasswordAuthentication no`;
- `KbdInteractiveAuthentication no`;
- `PermitRootLogin prohibit-password`;
- `MaxAuthTries 3`.

Дополнительно:

- `FACT` — permissions для WARP account/config secret-bearing files приведены к `0600 root:root`.
- `FACT` — `sshd -t` и effective-config assertions прошли до reload.
- `FACT` — выполнен только reload SSH service; VPS reboot не выполнялся.
- `FACT` — независимый post-change key-only SSH login завершился PASS.
- `FACT` — финальная effective config подтверждает password login disabled и root public-key-only.

## Post-change health

- `FACT` — WARP: `active/enabled`.
- `FACT` — IPv4 route после maintenance остаётся provider-direct.
- `FACT` — IPv6 route после maintenance остаётся через WARP table.
- `FACT` — `PP-LAB-I`, `PP-LAB-II`, `PP-LAB-III`: active.
- `FACT` — AmneziaWG container: active/up.
- `FACT` — systemd failed units: `0`.
- `DECISION` — maintenance verdict: `PASS`.

## Decisions

- `DECISION` — сохранить текущую схему WARP как IPv6-only; не переводить глобальный IPv4 egress в WARP на текущем основном узле.
- `DECISION` — не вводить автоматический cross-node failover для identity-sensitive applications: стабильность egress identity важнее автоматического переключения.
- `DECISION` — до появления принятого независимого backup node не выполнять disruptive rebuild/credential rotation текущего основного узла.

## Open items

- `TODO` — поднять отдельный provider-diverse backup node и провести его clean acceptance.
- `TODO` — после появления независимого backup node ротировать клиентские credentials текущих маршрутов, которые владелец хочет считать потенциально распространёнными/старыми, и удалить больше не нужные SSH identities.
- `TODO` — отдельно доказать reboot recovery WARP. `active + enabled` подтверждено, но реальный reboot в этом maintenance window намеренно не выполнялся.
- `TODO` — при необходимости оформить отдельный browser/app access acceptance для ChatGPT; не использовать bare curl 403 как достаточный verdict.

## Transferable lesson

Transport diversity на одном VPS не создаёт egress reputation diversity: переключение между VLESS/XHTTP/Hysteria на одном и том же provider IP не меняет IP-based anti-abuse reputation. Независимый egress path (например, отдельный provider node или аккуратно ограниченный WARP path) решает другой класс отказа, чем смена транспорта.
