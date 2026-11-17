# Secondary node — three-route deployment and Happ subscription

**Date:** 2026-11-17
**Delivery status:** DONE. Three routes deployed and checked end to end from Windows. One private HTTPS subscription delivered and verified externally.
**Android evidence:** Happ showed successful connection checks for all three original profiles over mobile data. The screenshots came before the grouped subscription.

## Матрица повторного развёртывания

Цель — на одном новом Ubuntu VPS поднять три независимых маршрута, доказать их работу и выдать владельцу одну закрытую HTTPS-подписку Happ. Сборщик начинает с этой матрицы и актуальных [правил репозитория](../../AGENTS.md). Все значения вида `__ИМЯ__` подставляются из входных данных или генерируются для нового узла. Исторические реквизиты узла из отчёта для новой сборки не нужны.

### 1. Входные данные и допуск

| Данные | Обязательный выбор |
| --- | --- |
| VPS | Целевой IPv4, регион, SSH-порт и пользователь, Ubuntu 24.04 amd64 с systemd. Доступ к root или проверенный sudo. Явно разрешённый объём изменений |
| Идентичность SSH | Отпечаток из доверенного канала и отдельный known-hosts. Только если владелец явно разрешил для этого узла, первый контакт по TOFU с записью причины. Проверять закреплённый ключ и при повторном входе, в том числе после reboot |
| Сеть | Зафиксировать ожидаемый внешний IPv4 VPS. Выбрать два свободных TCP-слушателя для I и II, отдельный UDP-слушатель для III, HTTPS-порт подписки и TCP-порт HTTP-01, если нужен. Номер TCP и UDP может совпадать |
| REALITY | Выбрать доступный с VPS TLS 1.3 cover с сертификатом для выбранного SNI и ALPN h2. Проверить через `openssl s_client` с валидацией HTTPS-имени. Один проверенный cover подходит для обоих маршрутов |
| HTTPS подписки | DNS-имя, подтверждённое внешним резолвером, либо сертификат на публичный IP. Для HTTP-01 обеспечить входящий TCP 80 и внешний HTTPS на выбранном порте |
| Happ | Имя группы, эмодзи флага, один владелец подписки. Для каждого профиля использовать общее имя с суффиксом I, II или III |
| Проверка | Внешний клиент Windows или Linux с TCP/UDP-доступом к VPS. Android и целевые операторы нужны для отдельной мобильной приёмки |

До записи снять read-only инвентаризацию ОС, архитектуры, портов, firewall, конфигураций, пользователей и units. Проверить источник пакетов, время VPS и доступность тестовых ресурсов. Сохранить приватно исходные состояния и boot ID. Перепроверить выбранные порты и пути непосредственно перед записью. При несовпадении ключа, конфликте, непонятном состоянии VPS или невозможности локального отката остановиться. Не отключать существующие службы ради освобождения порта. SSH-пароль, ключи, токены и исходные профили передавать только по приватному каналу и без аргументов командной строки.

### 2. Версии, конфигурации и запуск

Для повторения исторической сборки использовать официальные релизы Xray **26.11.9** и Hysteria2 **2.14.0** для архитектур VPS и внешнего тестового клиента. Получить точный SHA-256 из метаданных upstream release, сверить скачанные файлы и зафиксировать версии и хеши в приватном запуске. При переходе на другую версию сначала проверить синтаксис и совместимость. Не устанавливать бинарник с несовпавшим хешем.

Один системный пользователь, конфиг и unit на маршрут. Каждый unit запускает свою команду от собственного непривилегированного пользователя. В конфиге root-владелец, группа службы и режим `0640`, в каталоге `0750`. Для порта ниже 1024 выдать только `CAP_NET_BIND_SERVICE` через `AmbientCapabilities` и `CapabilityBoundingSet`. Проверить доступ к файлам и всем родительским каталогам от имени пользователя службы. В unit предусмотреть `Restart=on-failure`, `NoNewPrivileges=yes`, `After=network-online.target` и `WantedBy=multi-user.target`. Вызывать `systemd-analyze verify` и `systemctl daemon-reload` перед стартом.

#### I и II — Xray

На VPS вызвать `xray uuid` и `xray x25519` отдельно для каждого маршрута. Из вывода X25519 извлечь `PrivateKey` и `Password (PublicKey)` с учётом старых названий `PublicKey` и `Password`. Проверить, что оба ключа представлены 43-символьным Base64url без padding. В тестовых шаблонах приватный и публичный ключи обозначены `__PRIV__` и `__PUB__`. Отдельным вызовом `openssl rand -hex 8` получить short ID на каждый маршрут. Для II сгенерировать отдельный URL-путь через CSPRNG. Значения хранить приватно и без вывода в консоль.

Серверный шаблон для I, JSON. Подставлять порты как числа.

```json
{
  "log": {"loglevel": "warning"},
  "inbounds": [{
    "listen": "0.0.0.0",
    "port": "__PORT_I__",
    "protocol": "vless",
    "settings": {
      "clients": [{"id": "__UUID_I__", "flow": "xtls-rprx-vision"}],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "raw", "security": "reality",
      "realitySettings": {
        "target": "__COVER__:443",
        "serverNames": ["__COVER__"],
        "privateKey": "__PRIV__",
        "shortIds": ["__SHORT_I__"]
      }
    }
  }],
  "outbounds": [{"protocol": "freedom"}]
}
```

Для II заменить порт, UUID и оба материала REALITY на значения II, убрать `flow`, установить `network: xhttp` и добавить в `streamSettings` объект `xhttpSettings` с `path: __XHTTP_PATH__` и `mode: auto`. Запуск обоих units — `xray run -c CONFIG`. Перед каждым запуском проверить от сервисного пользователя командой `xray run -test -c CONFIG`.

Клиентский шаблон для I, JSON. Входной SOCKS-порт — свободный локальный порт тестового процесса.

```json
{
  "log": {"loglevel": "error"},
  "inbounds": [{"listen": "127.0.0.1", "port": "__LOCAL_SOCKS__", "protocol": "socks", "settings": {"auth": "noauth"}}],
  "outbounds": [{
    "protocol": "vless",
    "settings": {"vnext": [{"address": "__VPS_IPV4__", "port": "__PORT_I__", "users": [{"id": "__UUID_I__", "encryption": "none", "flow": "xtls-rprx-vision"}]}]},
    "streamSettings": {
      "network": "raw", "security": "reality",
      "realitySettings": {"fingerprint": "chrome", "serverName": "__COVER__", "password": "__PUB__", "shortId": "__SHORT_I__"}
    }
  }]
}
```

Для II применить те же замены, что на сервере. В клиентский `password` идёт публичное значение пары II. В URI экспорта для обоих VLESS-профилей задать `encryption=none`, `security=reality`, `sni`, `fp=chrome`, `pbk`, `sid`. Для I добавить `type=tcp` и `flow=xtls-rprx-vision`. Для II добавить `type=xhttp`, `mode=auto` и URL-кодированный `path`. Параметры и фрагменты формировать штатной URL-библиотекой.

#### III — Hysteria2

Сгенерировать отдельный случайный пароль и выделенный leaf TLS-сертификат для узла. Например, через `openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -sha256 -nodes -days 365` с SAN для выбранных имени и IP. Снять SHA-256 pin leaf через `openssl x509 -noout -fingerprint -sha256`. Никогда не экспортировать приватный ключ сертификата.

Серверный шаблон в YAML.

```yaml
listen: "0.0.0.0:__PORT_III__"
tls:
  cert: __CERT_PATH__
  key: __KEY_PATH__
auth:
  type: password
  password: __HY_PASSWORD__
```

Клиентский шаблон в YAML.

```yaml
server: "__VPS_IPV4__:__PORT_III__"
auth: __HY_PASSWORD__
tls:
  sni: __TLS_NAME__
  insecure: true
  pinSHA256: "__LEAF_SHA256__"
socks5:
  listen: "127.0.0.1:__LOCAL_SOCKS__"
```

Запуск — `hysteria server -c CONFIG` на VPS и `hysteria client -c CONFIG` на тестовом клиенте. Для показанного self-signed варианта разрешение стандартной проверки CA в клиенте отключается только при обязательном точном pin leaf. Перед выдачей проверить, что правильный pin даёт трафик, а изменённый — отказ. В URI Hysteria2 для Happ добавить `sni`, `insecure=1` и `pinSHA256` из 64 hex-символов без двоеточий. Если клиент не умеет проверять pin, остановиться или применить доверенный TLS-сертификат и стандартную проверку CA.

### 3. Порядок действий и критерии остановки

| Этап | Что делать | Условие перехода | При сбое |
| --- | --- | --- | --- |
| 1 | Сверить входные данные, SSH pin, состояние VPS, свободные порты, учётные записи и пути | Инвентаризация и план отката зафиксированы | Ничего не менять |
| 2 | Собрать, запустить и проверить I. Проверить restart и stop/start I | Три независимых клиентских подключения успешны до и после restart | Откатить только I |
| 3 | Повторить для II и проверить I, пока II остановлен и снова после его запуска | II прошёл собственные тесты, I прошёл регрессию | Откатить только II и повторно проверить I |
| 4 | Повторить для III по внешнему UDP, проверить I и II | III передаёт реальный трафик, I и II прошли регрессию | Откатить только III и перепроверить I и II |
| 5 | Перезагрузить разрешённый VPS, сверить изменение boot ID, enabled/active всех units. Повторить три новых соединения на каждый маршрут | Реальный трафик после перезагрузки через все три маршрута | Остановить приёмку и локализовать отказ. Сохранить факты |
| 6 | Собрать подписку, включить отдельный HTTPS listener и проверить извне | Три профиля, точный заголовок, доверенный TLS, 404 с неправильным токеном, тест продления PASS | Убрать только компоненты подписки. Перепроверить три маршрута |
| 7 | При наличии доступа к телефону импортировать подписку с VPN off, затем тестировать по одному маршруту на целевых сетях | Имя группы и флаги видны, реальный трафик и выходной IP подтверждены | Отметить точный неуспешный или непроверенный сценарий |

Каждый чистый клиентский тест запускает новый процесс, один outbound и локальный SOCKS5, проверяет DNS-имя через туннель (режим `--socks5-hostname` или эквивалент), HTTP и HTTPS с ненулевым телом, затем сравнивает два независимых ответа IP-сервисов с ожидаемым IPv4 VPS. После теста закрыть процесс, очистить временный конфиг, записать номер повтора, тип сети и вердикт. Проверка DNS через SOCKS сама по себе не означает отсутствия утечек DNS устройства. При наличии активного VPN на тестовом компьютере проверить выбранный интерфейс и пометить, шёл ли тест через существующий туннель. Для III при тайм-ауте сначала различить QUIC loopback и внешний UDP. Если внешний клиент использует сторонний TUN, повторить через физический интерфейс отдельным тестовым процессом или с другой внешней сети. Не менять глобальную маршрутизацию ради теста.

### 4. Одна ссылка Happ и её проверка

1. Сначала сгенерировать три рабочие строки подключения. В копиях заменить только фрагмент после `#` на URL-кодированные UTF-8 строки `<флаг> <имя> I`, `<флаг> <имя> II`, `<флаг> <имя> III`. Проверить побайтно, что часть до `#` совпала с исходником. Порядок строк — VLESS RAW, VLESS XHTTP, Hysteria2.
2. Объединить строки через LF, завершить LF, закодировать стандартным Base64. В HTTP-ответе передать `Profile-Title: base64:<Base64 имени группы в UTF-8>`, `Content-Type: text/plain; charset=utf-8` и `Cache-Control: private, no-store`. Тело содержит только Base64 трёх строк.
3. Сгенерировать токен пути через `secrets.token_urlsafe(32)` или эквивалент. Обслуживать только точный путь токена по HTTPS, возвращать 404 для любого другого. Отключить логирование URL и токена. Хранить тело, токен и TLS-ключ закрыто. Для Python TLS-сервиса использовать непривилегированный systemd unit, `DynamicUser=yes` и `LoadCredential` для PEM-цепочки, приватного ключа, токена и тела. Альтернативный HTTPS-сервер должен обеспечивать те же свойства.
4. Для публичного IP без подходящего DNS использовать Certbot версии, поддерживающей IP, например **5.4.0**. Выпуск через `certbot certonly --standalone --preferred-challenges http-01 --preferred-profile shortlived --ip-address IP` с отдельным `--cert-name` и выделенными каталогами конфигурации, работы и логов. Для валидного DNS-имени применить HTTPS-сертификат для имени с соответствующим challenge. Настроить автоматическое продление и deploy hook, перезапускающий только службу подписки. В staging проверить `certbot renew --dry-run --no-random-sleep-on-renew` с теми же каталогами. Для самого выпуска передать настройки учётной записи и согласие с ToS в одобренном объёме.
5. Из независимой сети запросить всю подписку с обычной проверкой доверия и имени/IP сертификата. Сверить ответ 200, заголовок и хеш полного тела, декодировать Base64, проверить ровно три разных профиля, порядок, декодированные имена и сохранность параметров подключения. Запросить путь с неверным токеном и ожидать 404. Перепроверить состояние всех VPN units. Выдать владельцу ровно один приватный URL для импорта в Happ.

**Итог воспроизведения.** Записать для этапов 1–7 `PASS`, `FAIL` или `PENDING` с коротким объяснением. Развёртывание и HTTPS-доставка завершены после этапов 1–6. Android-приёмка требует отдельного этапа 7. Прежний PASS другого узла в новый отчёт не переносится.

## Recovery notes

- FACT — The first Xray provisioning attempt stopped at key parsing and rolled back. The release used a combined public-key label in its output. Updating the parser and rerunning from a clean state resolved that failure.
- FACT — One Windows data-path probe timed out after a service restart. The original probe did not identify the endpoint in the error. The test was made more specific by using a faster HTTP probe, adding one bounded retry and reporting the failed probe name. The subsequent checks passed.
- FACT — Hysteria2 passed a real loopback data-path check while the default Windows path timed out at the QUIC handshake. Windows selected an existing Happ virtual adapter for the target. A process-local UDP relay pinned to the physical Windows interface permitted native Hysteria2 to pass externally. The relay did not change global routing or Happ settings. The specific cause of the timeout inside the former path was not established.
- FACT — The initial subscription attempt obtained a valid certificate, then the Windows SSH wrapper failed while printing a non-ASCII service-manager message. The transaction rolled back. Running the wrapper in UTF-8 and retrying resolved the issue. Test non-interactive terminal encoding before starting the transaction.

## Verification and limits

| Check | Result |
| --- | --- |
| Windows end-to-end data path, restarts and earlier-route regression | PASS for I, II and III |
| VPS reboot and fresh Windows connections | PASS, three per route |
| Android Happ with the original individual profiles | Successful in-app checks shown for I, II and III over mobile data |
| Private HTTPS subscription, exactly three profiles, title/labels and invalid token | PASS from an external Windows client |
| Certificate renewal simulation | PASS |
| Grouped subscription import, flag rendering and full traffic matrix on Android | Pending direct evidence |
| Android per-operator browser egress, independent DNS-leak testing and formal Wi-Fi/mobile matrix | Pending direct evidence |

The deployment and delivery are complete in the scope above. This record is a reproduction guide and evidence checkpoint for the secondary node. Formal acceptance of the grouped Android subscription and the original node's existing project status are tracked separately.
