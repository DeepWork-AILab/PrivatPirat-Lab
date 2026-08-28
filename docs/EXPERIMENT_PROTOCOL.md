# Протокол эксперимента PP-LAB-01

## 1. Текущее состояние

- `FACT` — публичная архитектурная рамка подготовлена.
- `FACT` — identity и read-only inventory `PP-LAB-01` подтверждены.
- `FACT` — `PP-LAB-I` прошёл полный `G2 PASS`: Wi-Fi и Android mobile data path, clean reconnect, independent exit-IP checks, restart recovery и stop/start recovery/isolation.
- `FACT` — `PP-LAB-II` построен как отдельный Xray instance/unit; Android/mobile acceptance II завершён PASS, включая 3/3 clean reconnect, restart recovery и stop/start recovery/isolation.
- `FACT` — после добавления II обязательная Android/mobile regression `PP-LAB-I` завершена 3/3 PASS.
- `DECISION` — маршруты принимаются последовательно и независимо.
- `DECISION` — mobile-часть `G3 / PP-LAB-II` принята как PASS.
- `DECISION` — формальный `G3` остаётся `PARTIAL`, пока не завершены Wi-Fi acceptance II и отдельная leak-oriented DNS-проверка II.
- `HYPOTHESIS` — все три маршрута могут быть воспроизводимо работоспособны в доступных Wi‑Fi- и мобильных сетях Российской Федерации.
- `TODO` — на доступной Wi-Fi сети завершить недостающий acceptance II и regression I; затем закрыть `G3`.

## 2. Gates

| Gate | Условие открытия | Условие закрытия |
|---|---|---|
| `G0 — Intake` | утверждены имя, границы и публичная рамка | `PASS` — отдельный репозиторий и границы зафиксированы |
| `G1 — Inventory` | получен SSH-доступ и проверен host-key fingerprint | `PASS` — read-only inventory выполнен, расхождение ресурсов принято отдельным решением владельца |
| `G2 — PP-LAB-I` | `G1 PASS` и согласован change packet | `PASS` — полный acceptance I, включая restart recovery и stop/start recovery/isolation |
| `G3 — PP-LAB-II` | `G2 PASS` | полный PASS II на целевых доступных сетях + regression PASS I |
| `G4 — PP-LAB-III` | `G3 PASS`, подтверждены домен и сертификат | полный PASS III и regression PASS I+II |

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

Единственный первый безопасный шаг — открыть SSH-сессию с проверкой заранее полученного fingerprint host key и выполнить один read-only inventory bundle без `sudo`, установки пакетов и изменения файлов.

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

**Current status:** `MOBILE PASS / FORMAL PARTIAL`.

Подтверждено на Android/mobile:

- server-side config test, отдельный service/listener и неизменность I — PASS;
- первичный data path II — PASS;
- clean reconnect II — `3/3 PASS`;
- restart recovery II — PASS;
- stop/start recovery/isolation II — PASS; при остановленном II маршрут I оставался active;
- обязательная mobile regression I после добавления II — `3/3 PASS`.

Один промежуточный отрицательный restart-result был признан дефектом test harness: административный SSH проходил через тот же перезапускаемый II и потерял control channel. Единственный различающий read-only check подтвердил восстановление II, сохранность I, SSH и data path; серверный отказ не подтвердился.

Открыто до формального `G3 PASS`:

- Wi-Fi acceptance `PP-LAB-II`;
- отдельная leak-oriented DNS-проверка II;
- контрольная regression `PP-LAB-I` на Wi-Fi после проверки II.

Текущая санитизированная запись: [`docs/evidence/PP-LAB-II-G3-MOBILE-PASS-2026-08-29.md`](evidence/PP-LAB-II-G3-MOBILE-PASS-2026-08-29.md).

## 8. Stage 4 — PP-LAB-III

1. До изменения подтвердить выбранный домен, DNS и способ получения доверенного TLS-сертификата.
2. Выбрать отдельный свободный UDP-порт.
3. Зафиксировать проверенную версию Hysteria2 и checksum upstream-артефакта.
4. Создать нового системного пользователя, каталог и unit III.
5. Сгенерировать новый пароль/credential и private key сертификата; не раскрывать их.
6. Проверить конфигурацию до запуска.
7. Выполнить полный data-path, restart и stop/start isolation tests III.
8. Проверить III в Wi‑Fi и mobile network, если обе реально доступны.
9. Повторить полные regression tests I и II.

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

IP, домены конфигурации, ports, UUID, ключи, Short ID, пароли, URI и сырые логи в публичную запись не входят.

## 12. Текущий checkpoint

`G2 — PP-LAB-I: PASS` зафиксирован в [`docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md`](evidence/PP-LAB-I-G2-PASS-2026-08-29.md).

`G3 — PP-LAB-II: MOBILE PASS / FORMAL PARTIAL` зафиксирован в [`docs/evidence/PP-LAB-II-G3-MOBILE-PASS-2026-08-29.md`](evidence/PP-LAB-II-G3-MOBILE-PASS-2026-08-29.md).

`G4 / PP-LAB-III` остаётся заблокированным до формального `G3 PASS`. Ближайший шаг — завершить Wi-Fi acceptance II, leak-oriented DNS check и Wi-Fi regression I.
