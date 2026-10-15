# LilFox Amsterdam — ночная read-only диагностика

- `FACT` — Evidence ID: `LILFOX-AM-READ-ONLY-2026-10-16`.
- `FACT` — новые сетевые наблюдения: 2026-10-15 21:45 UTC, то есть 16 октября по Москве.
- `FACT` — исходный `main`: `8b29c9cff517c0b114a4aee8f6f4745fa94411c3`.
- `DECISION` — разрешены read-only проверки и публикация этого отчёта в отдельной ветке/Draft PR. Изменения инфраструктуры, DNS, подписок, SSH-доверия, deployment и merge запрещены.
- `FACT` — текущий итог: `DIAGNOSIS=PARTIAL`, `SERVER_INSPECTION=BLOCKED`, `VPN_RESTORED=NOT_PROVEN`. Ни один маршрут не получает новый PASS.

## Источники и свежесть

| ID | Источник | Что подтверждает |
|---|---|---|
| S1 | [AGENTS.md](../../AGENTS.md), [SECURITY.md](../../SECURITY.md), [протокол](../EXPERIMENT_PROTOCOL.md), [README](../../README.md) на указанном main | Границы, публикация, критерии PASS |
| S2 | Приватный `LILFOX_AM_FULL_HANDOFF_2026-10-06.md`, modified 2026-10-14 20:24:55 UTC, §§20.30–20.37 | Последнее сохранённое состояние Amsterdam; это историческое evidence, не текущая серверная проверка |
| S3 | Предыдущая диагностика этой миссии, 15 октября около 21:05–21:07 UTC | DNS, ограничение облачного транспорта, ответы HTTP и TLS interception |
| S4 | Новые DoH и ограниченные HTTPS-пробы, 15 октября 21:45 UTC | Текущее расхождение DNS и ответ фронта при явном выборе нового адреса |
| S5 | Desktop Commander device inventory и проверка наличия облачных SSH prerequisites | Причина невозможности текущей SSH-диагностики |
| S6 | [Генератор](../../scripts/lilfox-family-bundle.py), [существующие тесты](../../tests/test_lilfox_family_bundle.py) | Раздельные delivery origin и адрес назначения маршрутов |

`FACT` — более старый [публичный deployment checkpoint](LILFOX-AM-DEPLOYMENT-CHECKPOINT-2026-10-04.md) не заменяет поздний приватный handoff. Текущая задача возобновляет read-only диагностику; старые разрешения на установку или исправления не используются.

`DECISION` — операционные адреса, hostnames, ports, usernames, fingerprints, персональные URL, credentials, конфиги и raw logs здесь не публикуются. `OLD_ADDRESS`, `CURRENT_ADDRESS`, `DELIVERY_HOST`, `LEGACY_CERT_HOST` — роли из приватного incident inventory, а не значения для копирования в production. Приватные источники не публикуются ссылками.

## Восстановленная архитектура

`FACT` — по S2 Amsterdam — отдельный VPS, не Primary DeepWork и не PP-LAB-01. На одном сервере находятся три независимых runtime и доставка статических файлов.

| Компонент | Архитектура по handoff | Последняя доступная проверка |
|---|---|---|
| I | Отдельный Xray, VLESS RAW/TCP REALITY/Vision | Исторически проверены unit/listener/runtime и один персональный candidate; клиентский HTTPS не прошёл |
| II | Отдельный Xray, VLESS XHTTP REALITY | Исторически active/listening; текущий data path не проверен |
| III | Отдельный Hysteria2, TLS/QUIC/UDP, персональная авторизация и certificate pinning | Исторически active/listening; текущий data path и pin не проверены |
| Delivery | Отдельный Caddy HTTPS, статические персональные Landing и subscription files | Сейчас получен ответ root при явном выборе CURRENT_ADDRESS через управляемый прокси |
| Happ | Шесть получателей, у каждого subscription из I/II/III | Старый owner-reported результат 18/18 не подтверждает состояние после смены адреса |

`FACT` — S6 использует `public_base` для Landing/subscription URL, а отдельный `host` — для адресов трёх VPN-профилей. HTML сохраняет ссылку subscription в metadata. Это разные контракты: исправление адресов внутри файлов не обновляет DNS, уже распространённые URL или импортированный профиль Happ.

`FACT` — hostname типа LEGACY_CERT_HOST кодирует прежний адрес. Исправление записи собственного DELIVERY_HOST не перенаправит автоматически такие старые ссылки. Какие именно origins использованы в шести действующих ссылках, без приватного manifest сейчас неизвестно.

## Новые доказательства

### DNS и HTTPS

`FACT` — по одному запросу A и AAAA на каждое из двух имён к Google Public DNS и Cloudflare DNS over HTTPS: восемь запросов, без перебора приватных путей.

| Проверка | Actual | Вывод |
|---|---|---|
| DELIVERY_HOST A, оба resolver | `matches_old=true`, `matches_current=false`, rcode=0, TTL=300 | Подтверждено текущее DNS-рассогласование |
| DELIVERY_HOST AAAA, оба resolver | Пустой ответ, rcode=0 | IPv6 fallback в наблюдаемом DNS отсутствует |
| LEGACY_CERT_HOST A, оба resolver | `matches_old=true`, `matches_current=false` | Старый origin всё ещё выбирает прежний адрес |
| LEGACY_CERT_HOST AAAA, оба resolver | Пустой ответ, rcode=0 | IPv6 fallback отсутствует |
| Обычный HTTPS root, оба hostname | curl exit=0, HTTP=502, CONNECT=200, body=150 bytes | Ошибка в наблюдаемом пути через облачный прокси; это не доказанный ответ VPS |
| HTTPS root с явным CURRENT_ADDRESS, оба hostname | curl exit=0, HTTP=404, CONNECT=200, body=9 bytes | HTTP-фронт отвечает по управляемому проксированному пути к новому адресу |

`FACT` — обычный и принудительный запросы сохраняли исходный hostname, SNI, HTTPS port и path `/`; различался только выбранный CONNECT destination. Использованы ограниченные connect/total timeouts, без redirect following и без отключения TLS verification. HTTP 502/404 не трактуется как успешная доставка из-за curl exit=0.

`FACT` — один дополнительный различающий verbose check для DELIVERY_HOST: обычный путь показал заголовок `server: mitmproxy`; принудительный CONNECT действительно указывал CURRENT_ADDRESS и получил `server: Caddy`, HTTP/2 404.

`FACT` — issuer предъявленного облачному curl сертификата — OpenAI, LLC / openai.com. Это TLS interception управляемого egress proxy. `ssl_verify_result=0` проверяет этот путь доверия, а не origin certificate VPS. Нельзя заключать, что действующий Caddy certificate корректен, действителен или соответствует персональным URL.

`FACT` — root 404 не проверяет tokenized Landing/subscription path. Статические персональные файлы по сети не запрашивались: актуальные приватные URL в облаке отсутствуют. Старый адрес не использовался для запросов с секретными путями/credentials.

`FACT` — предыдущий контроль S3 показал ENETUNREACH для прямых TCP sockets как к target, так и к независимому control. Поэтому этот облачный runtime не заменяет прямой TCP/UDP VPN-клиент. Повторять серию тех же raw probes без изменения среды не стали. Доступность UDP/QUIC этими HTTPS-проверками не устанавливается.

### Доступ к серверу

`FACT` — Desktop Commander при начальной и контрольной проверке показывает единственное зарегистрированное устройство Offline, last seen около девяти часов назад. Сообщение владельца о включённом ноутбуке не означает, что агент Desktop Commander подключён.

`FACT` — в облаке отсутствуют documented Amsterdam private identity, прежний known_hosts и приватный target workspace; SSH agent не настроен, стандартные private identities отсутствуют. Доступ к существующему WSL через подключённый инструмент не появился.

`DECISION` — SSH не запускался. Новый ключ не принимался, known_hosts не менялся, новый канал управления не создавался. Это конкретный blocker серверного этапа. Ограничение не обходилось установкой ПО, браузерным терминалом, другим VPS или сменой management VPN.

## Что установлено и что не установлено

| Класс | Статус | Минимальная причина / предел доказательства |
|---|---|---|
| DNS delivery | `FACT: FAIL` относительно CURRENT_ADDRESS | Два resolver направляют DELIVERY_HOST на OLD_ADDRESS после provider IP replacement |
| Ссылки с LEGACY_CERT_HOST | `FACT: stale resolution`; фактическое использование всеми получателями неизвестно | Само имя продолжает разрешаться в OLD_ADDRESS; правки другого DNS-имени недостаточно |
| Доставка всех шести персональных файлов | `TODO: NOT_RUN` | Нет приватного manifest и проверенного SSH; root 404 не заменяет шесть HTTP200 |
| Старые destination внутри server subscriptions | `FACT: historical fix`, текущий readback отсутствует | S2 §20.31: APPLIED, files=6, candidate hashes confirmed, protected routes/Caddy unchanged; повторная массовая замена не обоснована |
| I | `FACT: historical client failure`; причина `UNKNOWN` | S2 §§20.32–20.34: Android TLS/update errors и отдельный WSL curl exit35 после candidate config test; не доказана текущая серверная ошибка |
| II и III | `TODO: NOT_RUN` для текущего состояния | Нет свежей клиентской пробы или серверной сверки |
| Серверные units/listeners/config/certificates | `TODO: BLOCKED` | Текущий pinned SSH недоступен; исторический active не доказывает data path |
| Ограничение российских сетей | `HYPOTHESIS` | Историческая региональная асимметрия совместима с фильтрацией, но текущего синхронного RF/control comparison нет |

`FACT` — исторический WSL observer не зарегистрировал target traffic во время одной failed probe. Более поздний Android observer считал общий трафик, включая исходящий; связь окна с фактической попыткой телефона не установлена. Эти записи не позволяют объявить блокировку конкретного оператора, всей подсети или неисправность REALITY. Новая серверная ошибка в этой миссии не подтверждена.

`HYPOTHESIS` — часть Happ-клиентов сохраняет прежний профиль, потому что refresh идёт к старому delivery origin. Это объясняет возможную связь delivery и stale client destination; без проверки exact source URL и импортированного профиля причинная связь не подтверждена. Даже исправная доставка не гарантирует работоспособность I/II/III.

## Change packet — только проект, НЕ разрешение на применение

`DECISION` — ниже отдельные gates. Ни один из них не выполнялся. Только DNS имеет подтверждённый дефект; параметры будущего API-вызова должны быть получены агентом из разрешённого приватного inventory/control plane. Record IDs и свежий provider/DNS snapshot сейчас недоступны, поэтому исполняемый пакет ещё не готов. Для TLS и VPN точный mutation payload до диагностики придумывать нельзя.

### G0 — доступ и read-only preflight

`TODO` — когда существующий Desktop Commander снова доступен, использовать уже установленный WSL/OpenSSH. Требования: `BatchMode=yes`, `StrictHostKeyChecking=yes`, `UpdateHostKeys=no`, explicit documented identity и прежний target-specific known_hosts. Если прежняя pin привязана к старому адресу, использовать только уже документированный HostKeyAlias; не переносить trust вручную и не принимать TOFU. Нет нужного файла/совпадения ключа — STOP этого направления.

`TODO` — один ограниченный read-only snapshot Amsterdam: unit active/substate/NRestarts и MainPID; владельцы ожидаемых TCP/UDP listeners; соответствие runtime/config path и build; время/свободное место; metadata сертификатов и локальная проверка hostname/chain/expiry; локальный Caddy request с правильным Host/SNI. Только структурированные counts/booleans/error classes, без raw config/journal/process environment. Не запускать конфиг как второй сервер, не сохранять dumps на VPS.

`TODO` — из существующего приватного manifest точно сопоставить шесть получателей и шесть файлов; сверить hashes с последним receipt, по три профиля, суммарно 18 destinations, auth/transport/TLS соответствие серверу. Проверить отдельно Landing metadata URL, Happ source URL и route destination. Проверки ссылок — только после независимого подтверждения ownership destination и origin TLS; не отправлять secret paths старому адресу.

### G1 — исправление единственной подтверждённой DNS-записи

- `TODO` — цель: `DELIVERY_HOST / A / OLD_ADDRESS -> CURRENT_ADDRESS`, одна запись в существующей зоне. Не менять соседние записи, credentials, подписки, route runtimes, AAAA и TLS pins.
- `TODO` — preflight: provider подтверждает CURRENT_ADDRESS этому Amsterdam; control-plane read даёт ровно одну ожидаемую A-запись и DNS-only режим. Resolver TTL=300 не заменяет чтение control-plane TTL. Неожиданное содержимое — STOP и пересмотр пакета.
- `TODO` — точный будущий API shape: `PATCH /zones/{verified_zone_id}/dns_records/{verified_record_id}`, единственное поле payload `content=CURRENT_ADDRESS`. Сразу до PATCH повторить GET и сравнить type/name/content/ttl/proxied с backup; применять только при совпадении. Локальная compare-before-write не является атомарным CAS; при параллельном редактировании — STOP/согласовать окно.
- `TODO` — backup: приватный root-only snapshot существующей записи с IDs/type/name/content/ttl/proxied и временем, плюс подтверждение владения обоими адресами. Без записи на VPS и без backup в Git. В readback удостовериться, что менялось только content.
- `TODO` — Expected: authoritative/control-plane A и оба resolver выбирают CURRENT_ADDRESS; TTL и DNS-only режим сохранены. Персональная доставка — отдельный тест, не автоматический PASS.
- `TODO` — PASS: control-plane readback точен; после истечения прежнего TTL плюс разумного времени распространения оба resolver согласны; затем независимый HTTPS с настоящей origin TLS validation и проверка точных шести путей.
- `TODO` — rollback: восстановить content из snapshot ТОЛЬКО если прежний адрес всё ещё принадлежит владельцу и возврат безопасен. Provider replacement мог лишить владения OLD_ADDRESS; нельзя слепо откатывать на него. Если владение/безопасный rollback не подтверждены — gate закрыт до отдельного решения владельца.
- `TODO` — риск: низкий для изолированной A-правки, но возврат на чужой адрес опасен; DNS cache delay ожидаем. Влияние ограничено клиентами, реально использующими DELIVERY_HOST. LEGACY_CERT_HOST и stale imported profiles этим не исправляются.

### G2 — origin TLS и delivery, только при найденном расхождении

`TODO` — сначала без изменений проверить полный перечень используемых origins, Caddy routing/certificate binding, expiry и шесть HTTP200 responses через разрешённый независимый путь. Проверить тело Landing, metadata и по три корректных профиля в subscription; сравнения только внутри приватного процесса.

`TODO` — если найден mismatch, готовить ОДИН отдельный пакет для соответствующего слоя: certificate/hostname binding либо delivery-origin references. Существующие tokens/auth/pins сохранять; не регенерировать шесть bundles и не менять REALITY из-за TLS-ошибки доставки. Точный diff возможен только после G0. Backup: приватный snapshot только затрагиваемых файлов/metadata с hashes, permissions, ownership; rollback: восстановление только этих объектов с hash readback. Reload/restart, если потребуется, требует отдельного разрешения.

`TODO` — PASS: шесть exact Landing/subscription fetches с настоящим TLS, ненулевым ожидаемым body, правильным correspondence и 18 destination matches; затем фактический Happ refresh на клиенте. STOP: unexpected redirect/origin, key/pin drift, неоднозначный recipient mapping, чужие файлы, config validation FAIL или неподтверждённый rollback. Риск средний: ошибка затрагивает распространённые персональные ссылки.

### G3 — изоляция route failure, без предполагаемого исправления

`TODO` — после read-only сверки выбрать один точно идентифицированный профиль I. Через существующий независимый клиент выполнить одну ограниченную попытку и синхронно наблюдать только входящий трафик к нужному listener с известным source/time и положительным observer control; сверить счётчики с категоризированным journal. Общий счётчик всего трафика на том же номере порта не использовать. Не менять рабочий management VPN, TUN или default route.

`TODO` — если packets не приходят, сравнить тот же candidate из независимой разрешённой non-RF сети; исследовать путь, а не менять keys. Если приходят и отклоняются, сверить exact client/server transport/auth/TLS параметры, затем составить отдельный минимальный diff по доказанной причине. При первом FAIL — не более одного различающего read-only теста и STOP этого направления.

`TODO` — II и III проверять раздельно тем же принципом; III требует настоящего UDP/QUIC-клиента, HTTPS proxy его не заменяет. VPN mutation packet сейчас отсутствует: причины не установлены. Риск предположительных замен credentials/REALITY/pins высок; такие изменения не предложены.

`TODO` — operational data-path evidence: для каждого выбранного маршрута DNS, HTTP/HTTPS через независимые endpoints, два exit-IP checks (`match=true`), три clean reconnect repetitions, независимые RF mobile/Wi-Fi наблюдения. Итоговая матрица шести подписок × три маршрута — 18 отдельных результатов. Restart/isolation acceptance по протоколу остаётся отдельным будущим gate: нынешний запрет рестартов действует, полного нового formal PASS до этого нет.

## Проверки отчёта и оставшиеся ограничения

- `FACT` — существующий `test_lilfox_family_bundle.py`: 26 tests PASS в облаке на текущем main. Это проверка генератора, не серверной доставки или VPN.
- `FACT` — в ходе миссии нет записей/рестартов на VPS, DNS updates, изменений профилей или SSH trust; Primary DeepWork и PP-LAB-01 не использовались как targets/control hosts.
- `TODO` — перед публикацией: staged/full-diff Gitleaks с полной редакцией, ручная проверка отсутствия operational values, GitHub secret-check CI; результаты в Draft PR.
- `TODO` — не проверены текущие units/configs/certificates, exact шесть Landing/subscription paths, imported Happ profiles и I/II/III data path в нужных сетях.
- `FACT` — ближайшее полезное действие: read-only G0 через прежний pinned SSH, когда уже существующий инструмент подключится. До этого серверная часть STOP; ночные ручные операции от владельца не запрашивались.
