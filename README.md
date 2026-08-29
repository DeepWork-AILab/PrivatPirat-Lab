# PrivatPirat Lab

Экспериментальный проект по последовательному развёртыванию и доказательному тестированию трёх независимо выбираемых маршрутов на одном VPS и одном публичном IP.

**Статус:** `EXPERIMENTAL / Stage 4 — PASS`

**Узел:** `PP-LAB-01`

**Текущий факт:** `PP-LAB-I`, `PP-LAB-II` и `PP-LAB-III` формально приняты по действующему protocol baseline. I = VLESS RAW/TCP REALITY/Vision; II = VLESS XHTTP REALITY; III = Hysteria2 TLS/QUIC/UDP. Для всех маршрутов подтверждён полный data path; II и III прошли по 3/3 clean reconnect на Android/mobile и Wi-Fi, restart recovery и stop/start recovery/isolation. После добавления III обязательная regression I+II также прошла 3/3 на Wi-Fi и mobile. `G4 / PP-LAB-III = PASS`.

**Источник истины проекта:** ветка `main` этого репозитория.

## Цель

Проверить на реальных Wi‑Fi- и мобильных сетях Российской Федерации, можно ли воспроизводимо использовать три независимых маршрута:

| ID | Маршрут | Серверный компонент | Сетевой вход |
|---|---|---|---|
| `PP-LAB-I` | VLESS RAW/TCP REALITY/Vision | отдельный экземпляр Xray | отдельный TCP-порт |
| `PP-LAB-II` | VLESS XHTTP REALITY | отдельный экземпляр Xray | отдельный TCP-порт |
| `PP-LAB-III` | Hysteria2 TLS/QUIC/UDP | отдельный сервис Hysteria2 | отдельный UDP-порт |

Технически это три маршрута или транспортных профиля, а не три разные протокольные семьи: первые два используют VLESS, но различаются транспортом.

Цель проекта — не обещать работоспособность заранее, а получить проверяемый ответ. `Configuration OK`, открытый порт, handshake, ping, состояние `connected` или один открывшийся сайт не считаются PASS.

## Целевая схема

```text
клиент вручную выбирает один маршрут
                 │
          PP-LAB-01 / 1 IP
          ├─ TCP/<PORT_I>   → xray@pp-lab-i   → PP-LAB-I
          ├─ TCP/<PORT_II>  → xray@pp-lab-ii  → PP-LAB-II
          └─ UDP/<PORT_III> → hysteria2       → PP-LAB-III
```

Каждый маршрут запускается, останавливается, тестируется и используется независимо. Автоматическое переключение, балансировка, общий failover, Control Plane и subscription endpoint не входят в эксперимент.

Один VPS остаётся общей точкой отказа. Три маршрута на нём дают транспортное разнообразие, но не создают высокую доступность.

## Граница со Space Signal

`PrivatPirat Lab` — отдельный публичный лабораторный проект. Он:

- не переименовывает и не заменяет Space Signal;
- не изменяет ADR-003 и каноническую идентичность Space Signal;
- не делает `PP-LAB-01` узлом Alpha, Beta или Gamma;
- не включает результаты в формальную Триаду, Гексаду или Эннеаду;
- не меняет `DeepWork-AILab/Space-Signal` или его ветку `main`.

Если все три маршрута получили доказательный PASS, результат становится кандидатом на воспроизводимый шаблон одной узловой Триады. Формальное включение потребует отдельного архитектурного решения в Space Signal.

## Платформа эксперимента

- `FACT` — фактическая ОС: Ubuntu 24.04 LTS, `x86_64`;
- `FACT` — фактические ресурсы на момент inventory: 1 vCPU, около 1 GB RAM и около 14 GB корневого диска;
- `FACT` — используется один публичный адрес, который не публикуется в репозитории;
- `DECISION` — после обнаружения расхождения с первоначальным описанием тарифа владелец отдельно разрешил продолжить эксперимент на фактически инвентаризированной системе.

## Последовательность принятия

1. `Stage 0 — PASS` — границы, источники и отдельный публичный репозиторий зафиксированы.
2. `Stage 1 — PASS` — identity, SSH host key и read-only inventory подтверждены.
3. `Stage 2 — PASS` — `PP-LAB-I` прошёл Wi‑Fi и Android mobile data-path acceptance, clean reconnect, independent exit-IP checks, restart recovery и stop/start recovery/isolation.
4. `Stage 3 — PASS` — `PP-LAB-II` прошёл Android/mobile и Wi-Fi acceptance, leak-oriented DNS check, restart и stop/start isolation; `PP-LAB-I` прошёл обязательную regression на обеих сетях.
5. `Stage 4 — PASS` — `PP-LAB-III` построен как отдельный Hysteria2 service, прошёл mobile/Wi-Fi acceptance, leak-oriented DNS check, restart recovery, stop/start isolation; `PP-LAB-I` и `PP-LAB-II` прошли обязательную regression на обеих сетях.

Полный порядок и критерии описаны в [протоколе эксперимента](docs/EXPERIMENT_PROTOCOL.md).

## Текущий checkpoint — 2026-08-29

### G2 / PP-LAB-I

- `FACT` — Wi‑Fi: три чистых reconnect-повтора `PP-LAB-I` завершились с `DNS/HTTP/HTTPS PASS`; два независимых exit-IP endpoint согласились между собой и совпали с ожидаемым серверным выходом.
- `FACT` — независимый browser-based DNS leak test показал только сторонние публичные резолверы и не выявил DNS обычного провайдера; для текущего acceptance это зафиксировано как `DNS leak PASS`.
- `FACT` — mobile regression устранена минимальным изменением `fingerprint: chrome -> firefox`; серверная конфигурация, firewall и Xray для исправления не менялись.
- `FACT` — Android mobile data path после исправления прошёл DNS/HTTP/HTTPS и independent exit-IP checks; повторные clean reconnect подтверждены.
- `FACT` — отдельный passphrase-protected ED25519 SSH identity для POCO/Termux авторизован на PP-LAB-01; key-only login подтверждён.
- `FACT` — `restart recovery PASS` и `stop/start recovery/isolation PASS` подтверждены для I.
- `DECISION` — `G2 — PP-LAB-I: PASS`.

Финальная G2-запись: [`docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md`](docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md).

### G3 / PP-LAB-II

- `FACT` — PP-LAB-II создан как отдельный Xray instance/unit на отдельном входе с новыми client/server credentials; PP-LAB-I при построении II не переписывался.
- `FACT` — server-side config test, service state и listener для II прошли проверку; контрольная проверка подтвердила, что конфигурация I не изменилась.
- `FACT` — Android/mobile clean reconnect II: `3/3 PASS`; каждый раунд включал DNS/HTTP/HTTPS и два независимых exit-IP check.
- `FACT` — restart recovery II: PASS. Один промежуточный ложный отрицательный результат был вызван тем, что административный SSH проходил через тот же перезапускаемый маршрут; последующий различающий read-only check подтвердил восстановление обоих units, SSH и data path II.
- `FACT` — stop/start recovery/isolation II: PASS; во время остановки II `PP-LAB-I` остался active, затем II автоматически восстановился, полный data path вернулся.
- `FACT` — mobile regression `PP-LAB-I` после добавления II: `3/3 PASS`.
- `FACT` — Wi-Fi clean reconnect II: `3/3 PASS`; DNS/HTTP/HTTPS и два независимых exit-IP check прошли во всех раундах.
- `FACT` — browser-based leak-oriented DNS test на Wi-Fi при активном II не выявил резолверов обычного доступа; по принятой методике `DNS leak PASS`.
- `FACT` — Wi-Fi regression `PP-LAB-I` после добавления II: `3/3 PASS`.
- `DECISION` — `G3 — PP-LAB-II: PASS`.
- `SECURITY TODO` — при локальной попытке открыть client URI через Android intent рабочая URI однажды появилась в Termux traceback; значение не публикуется. Ротация client credentials может быть выполнена отдельным maintenance change packet.

Финальная G3-запись: [`docs/evidence/PP-LAB-II-G3-PASS-2026-08-29.md`](docs/evidence/PP-LAB-II-G3-PASS-2026-08-29.md).

### G4 / PP-LAB-III

- `FACT` — Hysteria2 `v2.12.1` установлен как отдельный service; upstream SHA-256 verification — PASS.
- `DECISION` — для лабораторного III вместо домена/ACME принят self-signed TLS с обязательным certificate pinning (`pinSHA256`). Plain `insecure` без pin не является принятой схемой.
- `FACT` — успешный server build подтвердил отдельный UDP listener, отдельный service identity/unit и неизменность конфигураций I/II.
- `FACT` — Android/mobile clean reconnect III: `3/3 PASS`; DNS/HTTP/HTTPS и два independent exit-IP check — PASS во всех раундах.
- `FACT` — Wi-Fi clean reconnect III: `3/3 PASS`; DNS/HTTP/HTTPS и два independent exit-IP check — PASS во всех раундах.
- `FACT` — browser-based leak-oriented DNS test на Wi-Fi при активном III не выявил резолверов обычного доступа; наблюдались только публичные Cloudflare/Google resolvers в США. По принятой методике `DNS leak PASS`.
- `FACT` — restart recovery III: PASS; процесс III сменился, I/II/III остались active, data path восстановился. Промежуточный local curl timeout классифицирован как дефект test harness, а не отказ маршрута.
- `FACT` — stop/start recovery/isolation III: PASS; при остановленном III I и II оставались active, затем III автоматически восстановился и полный data path вернулся.
- `FACT` — обязательная regression после добавления III: `PP-LAB-I` и `PP-LAB-II` каждый прошёл `3/3 PASS` на Wi-Fi и `3/3 PASS` на mobile.
- `DECISION` — `G4 — PP-LAB-III: PASS`.

Финальная G4-запись: [`docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md`](docs/evidence/PP-LAB-III-G4-PASS-2026-08-29.md).

## Связь с AI Symbiosis Field Notes

PrivatPirat Lab соответствует этой концепции **условно**: как кандидат на полевой кейс о том, как человек с помощью AI строит проверяемый технический процесс, обнаруживает ошибки, управляет риском и меняет собственный метод работы.

Сам факт настройки сетевого сервиса ещё не является кейсом AI‑симбиоза. Для этого необходимо фиксировать человеческие решения, предложения AI, независимые проверки, опровержения, цену внимания и общий переносимый вывод. Критерии вынесены в [AI_SYMBIOSIS_CASE.md](docs/AI_SYMBIOSIS_CASE.md).

Первый реальный опыт оформлен как [санитизированная evidence-запись](docs/evidence/PP-LAB-I-2026-08-17.md) и [статья-прототип](docs/field-notes/PP-LAB-I-FIRST-WORKING-PATH.md). Прототип не является финальным manual и не заменяет формальную приёмку маршрута.

## Project skills

- `FACT` — на текущем checkpoint в репозитории нет рабочего проектного `SKILL.md`.
- `FACT` — исторические упоминания возможных skills не являются установленными или проверенными артефактами.
- `TODO` — создавать skill только после появления повторяемого процесса, который действительно полезно автоматизировать и можно проверить без раскрытия operational secrets.

## Безопасность и публичность

Репозиторий намеренно не содержит рабочих конфигураций и секретов. Запрещено коммитить IP сервера без отдельного решения, SSH-ключи, UUID, REALITY private key/Short ID, пароли, домены/SNI/target, ключи сертификатов, working certificate pins, рабочие ссылки подключения, subscription URL, полные клиентские конфиги и сырые логи.

Перед каждым изменением обязательны: цель, минимальное действие, воздействие, Expected, проверка, backup, rollback и stop condition. Подробности — в [AGENTS.md](AGENTS.md) и [SECURITY.md](SECURITY.md).

## Актуальные upstream-источники

Перед реализацией версии и параметры проверяются повторно по первичным источникам:

- [Xray-core releases](https://github.com/XTLS/Xray-core/releases)
- [Project X: REALITY](https://xtls.github.io/en/config/transports/reality.html)
- [Project X: XHTTP](https://xtls.github.io/en/config/transports/xhttp.html)
- [Hysteria 2 releases](https://github.com/apernet/hysteria/releases)
- [Hysteria 2 server documentation](https://v2.hysteria.network/docs/getting-started/Server/)

Исторические конфиги допустимы только как структурная справка. Их IP, UUID, Short ID, ключи, пароли, домены/SNI/target и ссылки никогда не переносятся.

## Лицензия

Лицензия пока не выбрана. Публичная доступность репозитория сама по себе не предоставляет разрешение на копирование, распространение или создание производных работ. Решение о лицензии — отдельный TODO.
