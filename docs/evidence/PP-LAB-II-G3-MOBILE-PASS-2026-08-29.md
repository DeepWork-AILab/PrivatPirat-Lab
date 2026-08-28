# PP-LAB-II — G3 Mobile Acceptance Checkpoint — 2026-08-29

## Verdict

- `FACT` — `PP-LAB-II` на Android/mobile прошёл клиентский data-path acceptance, три clean reconnect-повтора, server-unit restart recovery и stop/start recovery/isolation.
- `FACT` — после добавления `PP-LAB-II` маршрут `PP-LAB-I` прошёл обязательный mobile regression: 3/3 clean reconnect с полным проверяемым data path.
- `DECISION` — mobile-часть `G3 / PP-LAB-II` принимается как `PASS`.
- `DECISION` — формальный `G3` остаётся `PARTIAL`, а не `PASS`: Wi-Fi acceptance `PP-LAB-II` ещё не выполнен; отдельная leak-oriented DNS-проверка для II также остаётся открытой до финальной приёмки.
- `TODO` — на доступной Wi-Fi сети выполнить клиентский acceptance `PP-LAB-II`, leak-oriented DNS check и контрольную regression-проверку `PP-LAB-I`. Только после этого закрывать `G3` и открывать `G4`.

## Evidence record

```text
Evidence ID: PP-LAB-II-G3-MOBILE-PASS-2026-08-29
UTC timestamp: 2026-08-28T22:25:00Z
Device-local checkpoint: 2026-08-29 01:25 UTC+3
Route: PP-LAB-II
Server software/version: Xray 26.3.27; checksum not re-recorded in this checkpoint
Client: Happ for Android; exact app version not independently captured in this checkpoint
Network class: mobile
Expected: independent PP-LAB-II operation with full mobile data path, repeatability, restart recovery, stop/start isolation, and no regression of accepted PP-LAB-I
Actual: PASS for the mobile acceptance scope
DNS resolution: PASS
HTTP: PASS
HTTPS: PASS
Exit-IP match via two independent endpoints: true
Clean reconnect repetitions: 3/3 PASS
Restart recovery: PASS
Stop/start recovery: PASS
Isolation from PP-LAB-I: PASS
PP-LAB-I regression after adding II: 3/3 PASS
Formal G3 verdict: PARTIAL
Reason: Wi-Fi acceptance and leak-oriented DNS check for II remain open
```

## Sanitized observations

1. `PP-LAB-II` был построен как отдельный Xray instance/unit и не переписал принятый `PP-LAB-I`.
2. До запуска конфигурация II прошла встроенную Xray config test; сервис и отдельный listener стартовали, а контрольная проверка показала, что конфигурация I не изменилась.
3. Первый mobile smoke test подтвердил DNS resolution, HTTP, HTTPS и совпадение exit IP с ожидаемым серверным выходом.
4. Три последовательных clean reconnect-повтора II дали полный `PASS`; оба независимых exit-IP endpoint каждый раз совпали с ожидаемым выходом.
5. При первом restart-check административный SSH проходил через тот же тестируемый маршрут II и потерял control channel во время перезапуска. Это дало ложный отрицательный результат harness, но не маршрута. Один различающий read-only check подтвердил: оба server units активны, SSH-доступ восстановлен, data path II снова `PASS`. Результат классифицирован как дефект тестового harness, а не отказ II.
6. В stop/start isolation test восстановление II было заранее запланировано server-side. Во время остановки II его unit стал `inactive`, а `PP-LAB-I` остался `active`; после автоматического start II снова стал `active`, и полный mobile data path восстановился.
7. Финальная regression `PP-LAB-I` после добавления II: 3/3 clean reconnect; DNS resolution, HTTP, HTTPS и два независимых exit-IP checks — `PASS` во всех трёх раундах.

## Security / publication boundary

В этот evidence намеренно не включены рабочий IP/hostname, порты, UUID/client IDs, REALITY key material, Short ID, SNI/target, XHTTP path, URI, subscription data, приватные ключи, пароли или сырые конфиги/логи.

Во время локальной клиентской интеграции рабочая URI однажды появилась в локальном Termux traceback при попытке открыть `vless://` через Android intent. Значение не переносится в GitHub/Drive. Ротация соответствующих client credentials может быть выполнена отдельным security-maintenance change packet после завершения функциональной приёмки.

## Gate state

```text
G0 — PASS
G1 — PASS
G2 / PP-LAB-I — PASS
G3 / PP-LAB-II — MOBILE PASS / FORMAL PARTIAL
G4 / PP-LAB-III — BLOCKED
```

Следующий полезный шаг: при доступной Wi-Fi сети выполнить недостающий Wi-Fi acceptance PP-LAB-II, leak-oriented DNS check и regression PP-LAB-I; затем оформить финальный `G3 PASS` отдельной evidence-записью.
