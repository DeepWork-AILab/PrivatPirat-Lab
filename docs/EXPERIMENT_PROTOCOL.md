# Протокол эксперимента PP-LAB-01

## 1. Текущее состояние

- `FACT` — публичная архитектурная рамка подготовлена.
- `FACT` — identity и read-only inventory `PP-LAB-01` подтверждены.
- `FACT` — `PP-LAB-I` прошёл полный `G2 PASS`: Wi-Fi и Android mobile data path, clean reconnect, independent exit-IP checks, restart recovery и stop/start recovery/isolation.
- `FACT` — `PP-LAB-II` прошёл полный `G3 PASS` на Android/mobile и Wi-Fi; после его добавления regression I прошла на обеих сетях.
- `FACT` — `PP-LAB-III` построен как отдельный Hysteria2 service и прошёл полный `G4 PASS` на Android/mobile и Wi-Fi.
- `FACT` — для III подтверждены 3/3 clean reconnect на обеих сетях, restart recovery, stop/start recovery/isolation и leak-oriented browser DNS check по принятой методике.
- `FACT` — после добавления III обязательная regression `PP-LAB-I` и `PP-LAB-II` завершена 3/3 PASS на Android/mobile и Wi-Fi для каждого маршрута.
- `DECISION` — маршруты принимаются последовательно и независимо.
- `DECISION` — `G4 / PP-LAB-III` принят как PASS.
- `DECISION` — трёхмаршрутный baseline `PP-LAB-I + PP-LAB-II + PP-LAB-III` завершён.
- `FACT` — один VPS остаётся общим failure domain; три маршрута дают транспортное разнообразие, но не host-level high availability.

## 2. Gates

| Gate | Условие открытия | Условие закрытия |
|---|---|---|
| `G0 — Intake` | утверждены имя, границы и публичная рамка | `PASS` — отдельный репозиторий и границы зафиксированы |
| `G1 — Inventory` | получен SSH-доступ; fingerprint заранее проверен либо владелец явно разрешил одноразовый TOFU | `PASS` — host key закреплён локально, read-only inventory выполнен, расхождение ресурсов принято отдельным решением владельца |
| `G2 — PP-LAB-I` | `G1 PASS` и согласован change packet | `PASS` — полный acceptance I, включая restart recovery и stop/start recovery/isolation |
| `G3 — PP-LAB-II` | `G2 PASS` | `PASS` — полный acceptance II на целевых сетях + regression PASS I |
| `G4 — PP-LAB-III` | `G3 PASS` и принят TLS design | `PASS` — полный acceptance III на целевых сетях + regression PASS I+II |

FAIL или неожиданный результат закрывает gate. Исправления не выполняются серией предположений: разрешён один различающий read-only тест, затем новое решение человека.

## 3. Change packet

Перед первым и каждым следующим изменением зафиксировать:

```text
Target:
Reason:
Exact command(s):
Impact:
Expected:
Verification:
Backup:
Rollback:
Stop condition:
Human approval:
Actual:
Verdict:
```

Команды с секретами не вставляются в публичные документы или чат. Для интерактивного ввода и локальной генерации используется способ, не раскрывающий секрет в command line, history или process list.

## 4. Stage 0 — intake и границы

1. Зафиксировать `PP-LAB-01` как `EXPERIMENTAL`.
2. Подтвердить, что это отдельный проект, а не узел канонической Триады Space Signal.
3. Разделить сведения на `FACT`, `DECISION`, `HYPOTHESIS`, `TODO`.
4. Проверить первичные upstream-источники и пометить исторические образцы как справочные.
5. Не менять VPS.

## 5. Stage 1 — read-only inventory

Единственный первый безопасный шаг — закрепить SSH host key, открыть SSH-сессию со строгой проверкой закреплённого ключа и выполнить один read-only inventory bundle без установки пакетов и изменения файлов. Нормальный режим использует заранее проверенный fingerprint. Если независимая provider console недоступна, владелец может отдельным решением разрешить одноразовый `TOFU`: впервые предъявленный ED25519 key закрепляется локально, не считается независимо аутентифицированным и при любом последующем изменении вызывает STOP.

Inventory должен подтвердить:

- hostname, machine-id в санитизированной форме и SSH host key;
- ОС, kernel, architecture, uptime;
- CPU, RAM, swap и disk;
- сетевые интерфейсы и наличие IPv4/IPv6;
- слушающие TCP/UDP sockets;
- firewall state;
- установленные релевантные пакеты;
- релевантные systemd units;
- исходящую TCP/UDP-доступность без изменения конфигурации.

Полный сырой вывод остаётся приватным. Неожиданно занятый порт, неизвестная конфигурация или расхождение ресурсов означает STOP.

## 6. Stage 2 — PP-LAB-I

1. Выбрать свободный отдельный TCP-порт после inventory.
2. Зафиксировать проверенную версию Xray и checksum upstream-артефакта.
3. Создать отдельного системного пользователя, каталог конфигурации и systemd unit только для I.
4. Локально сгенерировать новый UUID, REALITY key pair и Short ID.
5. До запуска выполнить проверку конфигурации.
6. Запустить только unit I и подтвердить service state как промежуточный факт.
7. Выполнить полный data-path test.
8. Перезапустить unit I и повторить data-path test.
9. Остановить I и подтвердить, что именно I недоступен; снова запустить и проверить восстановление.
10. Оформить PASS/FAIL с санитизированным evidence.

**Current verdict:** `PASS` — финальная запись: [`docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md`](evidence/PP-LAB-I-G2-PASS-2026-08-29.md).

## 7. Stage 3 — PP-LAB-II

1. Не менять файлы, unit, порт и секреты I.
2. Выбрать другой свободный TCP-порт.
3. Создать отдельный экземпляр Xray с новым UUID, REALITY key pair и Short ID.
4. Проверить конфигурацию II до запуска.
5. Выполнить полный data-path, restart и stop/start isolation tests II.
6. Повторить полный regression test I.
7. При деградации I — STOP; II не принимается.

**Current verdict:** `PASS`.

Подтверждено:

- server-side config test, отдельный service/listener и неизменность I — PASS;
- Android/mobile clean reconnect II — `3/3 PASS`;
- Wi-Fi clean reconnect II — `3/3 PASS`;
- DNS resolution / HTTP / HTTPS / два независимых exit-IP check — PASS во всех acceptance rounds;
- restart recovery II — PASS;
- stop/start recovery/isolation II — PASS; при остановленном II маршрут I оставался active;
- leak-oriented browser DNS test на Wi-Fi — PASS по принятой проектной методике;
- обязательная regression I после добавления II — `3/3 PASS` на Android/mobile и `3/3 PASS` на Wi-Fi.

Один промежуточный отрицательный restart-result был признан дефектом test harness: административный SSH проходил через тот же перезапускаемый II и потерял control channel. Единственный различающий read-only check подтвердил восстановление II, сохранность I, SSH и data path; серверный отказ не подтвердился.

Финальная санитизированная запись: [`docs/evidence/PP-LAB-II-G3-PASS-2026-08-29.md`](evidence/PP-LAB-II-G3-PASS-2026-08-29.md).

## 8. Stage 4 — PP-LAB-III

**Current verdict:** `PASS`.

Принятая архитектура:

- отдельный Hysteria2 service;
- отдельный system user, config и systemd unit;
- отдельный UDP listener;
- Hysteria2 `v2.12.1`, скачанный бинарник прошёл upstream SHA-256 verification;
- для лабораторного III вместо домена/ACME принят self-signed TLS с обязательным certificate pinning (`pinSHA256`);
- plain `insecure` без pin не является принятой схемой.

Подтверждено:

- successful config/bind test и service start — PASS;
- неизменность конфигураций I и II после build III — PASS;
- Android/mobile clean reconnect III — `3/3 PASS`;
- Wi-Fi clean reconnect III — `3/3 PASS`;
- DNS resolution / HTTP / HTTPS / два независимых exit-IP check — PASS во всех acceptance rounds;
- leak-oriented browser DNS test на Wi-Fi — PASS по принятой методике: резолверы обычного доступа не обнаружены;
- restart recovery III — PASS; процесс III сменился, I/II/III остались active, data path восстановился;
- stop/start recovery/isolation III — PASS; при остановленном III I и II оставались active, затем III автоматически восстановился и полный data path вернулся;
- обязательная regression после добавления III: `PP-LAB-I` и `PP-LAB-II` каждый прошёл `3/3 PASS` на Wi-Fi и `3/3 PASS` на Android/mobile.

Первый build III был остановлен из-за несовпавшего пути к checksum asset для ранее планировавшейся версии. Автоматический rollback подтвердил чистое состояние, I/II остались active, UDP listener освободился. После distinguishing read-only diagnostic build plan был отдельно переутверждён для `v2.12.1` и завершён PASS.

Во время restart test ожидаемый локальный `curl` timeout завершил shell из-за дефекта harness. Один read-only post-restart diagnostic подтвердил `III_DATA_PATH=PASS`, active I/II/III и смену PID III; отказ маршрута не подтвердился.

Финальная санитизированная запись: [`docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md`](evidence/PP-LAB-III-G4-PASS-2026-08-29.md).

## 9. Минимальный data-path PASS

Маршрут получает PASS только когда в каждой доступной целевой сети подтверждены все пункты:

1. Клиент стартует из чистого состояния с явно выбранным одним маршрутом.
2. DNS-запросы разрешаются ожидаемым способом без обнаруженной утечки.
3. Через маршрут загружаются HTTP- и HTTPS-ресурсы не менее чем с двух независимых test endpoints; фиксируются status и ненулевой body.
4. Два независимых сервиса определения exit IP согласуются между собой и совпадают с серверным выходом; публично сохраняется только результат `match=true/false`.
5. Полный набор повторяется не менее трёх раз после чистого reconnect клиента.
6. После restart серверного unit маршрут снова проходит полный набор.
7. Stop/start конкретного маршрута не нарушает другие принятые маршруты.
8. После добавления нового маршрута предыдущие маршруты проходят полный regression test.

Если одна из целевых сетей временно недоступна, verdict маркируется `PARTIAL`, а не `PASS`, пока недостающий тест не выполнен. Ограниченная проверка может быть явно принята человеком только как отдельный экспериментальный результат, не как общий PASS для Wi‑Fi и mobile.

## 10. Backup и rollback

Перед изменением:

- сохранить приватный timestamped snapshot затрагиваемых файлов с root-only permissions;
- зафиксировать package/version/checksum и исходное состояние unit;
- сохранить релевантный firewall snapshot до любой будущей правки firewall;
- не смешивать backup разных маршрутов;
- проверить, что restore-команда однозначна и не затрагивает соседние units;
- иметь сохранённую активную SSH-сессию при изменениях, способных повлиять на сеть.

Rollback удаляет или восстанавливает только компонент текущего шага, затем проверяет исходное состояние и регрессию уже принятых маршрутов. Если rollback нельзя проверить заранее, изменение запрещено.

## 11. Evidence record

Публичная запись результата содержит:

```text
Evidence ID:
UTC timestamp:
Route:
Server software/version/checksum:
Client software/version:
Network class: Wi-Fi | mobile
Expected:
Actual (sanitized):
DNS: PASS | FAIL
HTTP: PASS | FAIL
HTTPS: PASS | FAIL
Exit-IP match: true | false
Repetitions:
Restart recovery: PASS | FAIL
Isolation: PASS | FAIL
Regression:
Verdict: PASS | PARTIAL | FAIL
```

IP, домены конфигурации, ports, UUID, ключи, certificate pins, Short ID, пароли, URI и сырые логи в публичную запись не входят.

## 12. Финальный checkpoint

`G2 — PP-LAB-I: PASS` — [`docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md`](evidence/PP-LAB-I-G2-PASS-2026-08-29.md).

`G3 — PP-LAB-II: PASS` — [`docs/evidence/PP-LAB-II-G3-PASS-2026-08-29.md`](evidence/PP-LAB-II-G3-PASS-2026-08-29.md).

`G4 — PP-LAB-III: PASS` — [`docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md`](evidence/PP-LAB-III-G4-PASS-2026-08-29.md).

Текущий экспериментальный baseline завершён: три маршрута приняты. Следующие изменения относятся уже к отдельным maintenance, hardening или архитектурным этапам и требуют новых change packets.
