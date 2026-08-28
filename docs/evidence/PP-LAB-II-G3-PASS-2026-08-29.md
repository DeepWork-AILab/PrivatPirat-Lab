# PP-LAB-II — G3 PASS — 2026-08-29

## Verdict

- `FACT` — `PP-LAB-II` прошёл полный acceptance на Android/mobile и Wi-Fi по действующему протоколу.
- `FACT` — подтверждены data path, 3/3 clean reconnect на обеих целевых сетях, server-unit restart recovery и stop/start recovery/isolation.
- `FACT` — leak-oriented browser DNS test на Wi-Fi не выявил резолверов обычного доступа; наблюдались только сторонние публичные Google resolvers в США.
- `FACT` — после добавления `PP-LAB-II` ранее принятый `PP-LAB-I` прошёл обязательную regression-проверку на mobile и Wi-Fi: 3/3 clean reconnect с полным data path на каждой сети.
- `DECISION` — `G3 / PP-LAB-II: PASS`.
- `DECISION` — `G4 / PP-LAB-III` разблокирован, но серверные изменения Stage 4 не начинаются до отдельного preflight и подтверждения домена/DNS/способа получения доверенного TLS-сертификата.

## Evidence record

```text
Evidence ID: PP-LAB-II-G3-PASS-2026-08-29
UTC timestamp: 2026-08-28T22:47:00Z
Device-local checkpoint: 2026-08-29 01:47 UTC+3
Route: PP-LAB-II
Server software/version: Xray 26.3.27; checksum not re-recorded in this checkpoint
Client: Happ for Android; exact app version not independently captured in this checkpoint
Networks: Android mobile + Wi-Fi
Expected: independent PP-LAB-II operation with reproducible full data path, restart recovery, stop/start isolation, no DNS leak detected by the accepted browser method, and no regression of PP-LAB-I
Actual: PASS
DNS resolution: PASS
HTTP: PASS
HTTPS: PASS
Exit-IP match via two independent endpoints: true
Mobile clean reconnect: 3/3 PASS
Wi-Fi clean reconnect: 3/3 PASS
Restart recovery: PASS
Stop/start recovery: PASS
Isolation from PP-LAB-I: PASS
PP-LAB-I mobile regression after adding II: 3/3 PASS
PP-LAB-I Wi-Fi regression after adding II: 3/3 PASS
Leak-oriented browser DNS check on Wi-Fi: PASS for the accepted project method
Verdict: PASS
```

## Sanitized observations

1. `PP-LAB-II` построен как отдельный Xray instance/unit на отдельном сетевом входе с новым набором client/server credentials; файлы, unit, port и secrets принятого `PP-LAB-I` не переписывались.
2. До запуска конфигурация II прошла встроенный Xray config test; service/listener II стартовали, а контрольная проверка подтвердила неизменность I.
3. Mobile smoke test II подтвердил DNS resolution, HTTP, HTTPS и совпадение exit IP с ожидаемым серверным выходом.
4. Mobile acceptance II: три последовательных clean reconnect дали полный `PASS`; оба независимых exit-IP endpoint каждый раз совпадали с ожидаемым серверным выходом.
5. Restart recovery II: PASS. Один промежуточный отрицательный результат был вызван дефектом test harness — административный SSH проходил через тот же перезапускаемый II и потерял control channel. Единственный различающий read-only check подтвердил, что оба Xray units активны, SSH восстановлен и data path II снова `PASS`; серверный отказ не подтвердился.
6. Stop/start recovery/isolation II: PASS. Server-side auto-recovery был запланирован до stop. Во время остановки II его unit стал `inactive`, а `PP-LAB-I` остался `active`; после автоматического start II снова стал `active`, и полный data path восстановился.
7. Mobile regression I после добавления II: 3/3 clean reconnect; DNS/HTTP/HTTPS и два independent exit-IP check — `PASS` во всех раундах.
8. Wi-Fi acceptance II: 3/3 clean reconnect; DNS/HTTP/HTTPS и два independent exit-IP check — `PASS` во всех раундах.
9. Leak-oriented browser DNS test на Wi-Fi при активном II завершился без обнаружения резолверов обычного доступа; список состоял из сторонних публичных Google resolvers в США. В рамках принятой для проекта browser-based проверки это зафиксировано как `DNS leak PASS`.
10. Wi-Fi regression I после добавления II: 3/3 clean reconnect; DNS/HTTP/HTTPS и два independent exit-IP check — `PASS` во всех раундах.

## Security / publication boundary

В evidence намеренно не включены рабочий IP/hostname, ports, UUID/client IDs, REALITY key material, Short ID, SNI/target, XHTTP path, URI, subscription data, приватные ключи, пароли или сырые configs/logs.

Во время локальной клиентской интеграции рабочая URI однажды появилась в локальном Termux traceback при попытке открыть `vless://` через Android intent. Значение не переносится в GitHub/Drive. Ротация соответствующих client credentials остаётся отдельным security-maintenance TODO и не меняет результат функционального `G3 PASS`.

## Gate state

```text
G0 — PASS
G1 — PASS
G2 / PP-LAB-I — PASS
G3 / PP-LAB-II — PASS
G4 / PP-LAB-III — OPEN FOR PREFLIGHT
```

Следующий полезный шаг: Stage 4 preflight для `PP-LAB-III` — сначала подтвердить домен/DNS и способ получения доверенного TLS-сертификата; только затем формировать отдельный R3 change packet для серверных изменений.
