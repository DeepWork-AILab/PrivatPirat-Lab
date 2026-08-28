# PrivatPirat Lab

Экспериментальный проект по последовательному развёртыванию и доказательному тестированию трёх независимо выбираемых маршрутов на одном VPS и одном публичном IP.

**Статус:** `EXPERIMENTAL / Stage 2 — PASS`

**Узел:** `PP-LAB-01`

**Текущий факт:** `PP-LAB-I` принят по `G2`. На Wi‑Fi подтверждены три чистых reconnect-повтора с `DNS/HTTP/HTTPS PASS` и совпадением exit IP; независимый browser-based DNS leak test не обнаружил утечки к обычному провайдеру. Мобильная регрессия `PP-LAB-I` устранена на Android минимальным клиентским изменением `fingerprint: chrome -> firefox`; после этого подтверждены мобильный data path, повторные reconnect, server-unit restart recovery и stop/start recovery/isolation. `G2 PASS` достигнут; `Stage 3 / G3 — PP-LAB-II` разблокирован.

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

Порты, домен, REALITY target/SNI и версии ПО не назначаются до read-only inventory и проверки актуальной upstream-документации. Каждый маршрут должен запускаться, останавливаться, тестироваться и использоваться независимо. Автоматическое переключение, балансировка, общий failover, Control Plane и subscription endpoint не входят в эксперимент.

Один VPS остаётся общей точкой отказа. Три маршрута на нём исследуют транспортное разнообразие, но не создают высокую доступность.

## Граница со Space Signal

`PrivatPirat Lab` — отдельный публичный лабораторный проект. Он:

- не переименовывает и не заменяет Space Signal;
- не изменяет ADR-003 и каноническую идентичность Space Signal;
- не делает `PP-LAB-01` узлом Alpha, Beta или Gamma;
- не включает результаты в формальную Триаду, Гексаду или Эннеаду;
- не меняет `DeepWork-AILab/Space-Signal` или его ветку `main`.

Если все три маршрута получат доказательный PASS, результат станет лишь кандидатом на воспроизводимый шаблон одной узловой Триады. Формальное включение потребует отдельного архитектурного решения в Space Signal.

## Платформа эксперимента

- `FACT` — фактическая ОС: Ubuntu 24.04 LTS, `x86_64`;
- `FACT` — фактические ресурсы на момент inventory: 1 vCPU, около 1 GB RAM и около 14 GB корневого диска;
- `FACT` — используется один публичный адрес, который не публикуется в репозитории;
- `DECISION` — после обнаружения расхождения с первоначальным описанием тарифа владелец отдельно разрешил продолжить эксперимент на фактически инвентаризированной системе.

## Последовательность принятия

1. `Stage 0 — PASS` — границы, источники и отдельный публичный репозиторий зафиксированы.
2. `Stage 1 — PASS` — identity, SSH host key и read-only inventory подтверждены.
3. `Stage 2 — PASS` — `PP-LAB-I` прошёл Wi‑Fi и Android mobile data-path acceptance, clean reconnect, independent exit-IP checks, restart recovery и stop/start recovery/isolation.
4. `Stage 3 — OPEN` — `PP-LAB-II` может начинаться; при его приёмке обязателен regression test `PP-LAB-I`.
5. `Stage 4 — BLOCKED` — `PP-LAB-III` не начинается до формального закрытия `G3`.

Следующий этап открывается только после PASS предыдущего gate. Полный порядок и критерии описаны в [протоколе эксперимента](docs/EXPERIMENT_PROTOCOL.md).

## Текущий checkpoint — 2026-08-29

- `FACT` — Wi‑Fi: три чистых reconnect-повтора `PP-LAB-I` завершились с `DNS/HTTP/HTTPS PASS`; два независимых exit-IP endpoint согласились между собой и совпали с ожидаемым серверным выходом.
- `FACT` — независимый browser-based DNS leak test показал только сторонние публичные резолверы и не выявил DNS обычного провайдера; для текущего acceptance это зафиксировано как `DNS leak PASS`.
- `FACT` — mobile regression устранена минимальным изменением `fingerprint: chrome -> firefox`; серверная конфигурация, firewall и Xray для исправления не менялись.
- `FACT` — Android mobile data path после исправления прошёл DNS/HTTP/HTTPS и independent exit-IP checks; повторные clean reconnect подтверждены.
- `FACT` — отдельный passphrase-protected ED25519 SSH identity для POCO/Termux авторизован на PP-LAB-01; key-only login подтверждён.
- `FACT` — read-only inspection подтвердил, что активный `xray.service` обслуживает inbound структуры VLESS / RAW / REALITY / Vision, соответствующий PP-LAB-I.
- `FACT` — `restart recovery PASS`: после restart Xray сервис вернулся в `active`, процесс был перезапущен, и полный data path восстановился.
- `FACT` — `stop/start recovery/isolation PASS`: при остановке route стал недоступен, затем серверный unit был восстановлен, после чего DNS/HTTP/HTTPS и два exit-IP check снова прошли.
- `DECISION` — `G2 — PP-LAB-I: PASS`. `Stage 3 / G3 — PP-LAB-II` разблокирован.
- `SECURITY TODO` — обнаружен старый рабочий credential/URI в локальной PowerShell history; секрет не публиковался. Remediation и ротация вынесены в Issue #5.

Финальная санитизированная запись: [`docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md`](docs/evidence/PP-LAB-I-G2-PASS-2026-08-29.md).

## Связь с AI Symbiosis Field Notes

PrivatPirat Lab соответствует этой концепции **условно**: как кандидат на полевой кейс о том, как человек с помощью AI строит проверяемый технический процесс, обнаруживает ошибки, управляет риском и меняет собственный метод работы.

Сам факт настройки сетевого сервиса ещё не является кейсом AI‑симбиоза. Для этого необходимо фиксировать человеческие решения, предложения AI, независимые проверки, опровержения, цену внимания и общий переносимый вывод. Критерии вынесены в [AI_SYMBIOSIS_CASE.md](docs/AI_SYMBIOSIS_CASE.md).

Первый реальный опыт оформлен как [санитизированная evidence-запись](docs/evidence/PP-LAB-I-2026-08-17.md) и [статья-прототип](docs/field-notes/PP-LAB-I-FIRST-WORKING-PATH.md). Прототип не является финальным manual и не заменяет формальную приёмку маршрута.

## Project skills

- `FACT` — на текущем checkpoint в репозитории нет рабочего проектного `SKILL.md`.
- `FACT` — исторические упоминания возможных skills не являются установленными или проверенными артефактами.
- `TODO` — создавать skill только после появления повторяемого процесса, который действительно полезно автоматизировать и можно проверить без раскрытия operational secrets.

## Безопасность и публичность

Репозиторий намеренно не содержит рабочих конфигураций и секретов. Запрещено коммитить IP сервера без отдельного решения, SSH-ключи, UUID, REALITY private key/Short ID, пароли, домены/SNI/target, ключи сертификатов, рабочие ссылки подключения, subscription URL, полные клиентские конфиги и сырые логи.

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
