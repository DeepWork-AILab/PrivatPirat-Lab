# LilFox Amsterdam — read-only diagnosis и пакет восстановления

- `FACT` — Evidence ID: `LILFOX-AM-READ-ONLY-2026-10-16`; отчёт обновлён после подключения Desktop Commander.
- `FACT` — основные сетевые и серверные наблюдения: 15 октября 2026, 21:45–22:14 UTC (16 октября, 00:45–01:14 МСК).
- `FACT` — исходный main: `8b29c9cff517c0b114a4aee8f6f4745fa94411c3`.
- `DECISION` — разрешены диагностика и этот документ в отдельной ветке/Draft PR. Изменения VPS/DNS/действующих подписок, SSH trust, deployment и merge не разрешены.
- `FACT` — `VPN_RESTORED=NOT_PROVEN`. Есть свежий успешный Windows HTTPS data path I и II, но нет новой Android-матрицы, III client test или formal acceptance.

## Текущий диагноз

| Слой | Статус | Подтверждённое наблюдение |
|---|---|---|
| DNS собственного delivery hostname | `FACT: FAIL` относительно текущего адреса | Google и Cloudflare DoH возвращают прежний адрес, TTL=300; AAAA нет |
| Origins в шести Landing | `FACT: discrepancy` | Три metadata URL используют собственный hostname, три — legacy hostname, кодирующий прежний адрес; оба имени выбирают прежний адрес |
| Caddy и origin TLS | `FACT: local checks PASS` | Оба hostname проходят настоящее chain/hostname verification с localhost VPS; root HTTP404 ожидаем |
| Статические файлы | `FACT: local checks PASS` | Шесть Landing и шесть subscription: HTTP200, полные bodies совпадают с диском по SHA-256 |
| Серверные профили | `FACT: checked fields match` | Шесть файлов × три маршрута: 18 текущих destinations; auth/transport/REALITY public keys и pin III согласованы |
| I | `FACT: BASIC_HTTPS_EXIT=PASS` | Один точный текущий candidate, нативный Windows Xray: два независимых HTTPS200, оба exit-IP match |
| II | `FACT: BASIC_HTTPS_EXIT=PASS` | Отдельный точный candidate, тот же изолированный метод: два HTTPS200, оба exit-IP match |
| III | `TODO: client NOT_RUN` | Серверные config/auth/pin/listener/cert validity проверены; независимого UDP/QUIC-клиентского результата нет |
| Внешний HTTPS delivery с ноутбука | `FACT: attempted requests failed` | Несмотря на успешный native TCP control, полноценные запросы к текущему адресу timeout; при наблюдаемом curl root request до delivery listener не дошёл ни один пакет |
| Российские mobile/Wi-Fi и шесть Happ installs | `TODO: NOT_RUN` | Текущая среда ноутбука с TUN/прокси не заменяет независимый Android и прямую RF-сеть |

`FACT` — минимальные подтверждённые дефекты доставки: stale A собственного домена и три ссылки metadata на legacy origin. Одной A-правки недостаточно для этих трёх страниц. Перезаписывать server subscriptions ради адреса не требуется: текущий readback подтверждает предыдущую правку всех 18 destinations.

`FACT` — текущие I/II нельзя объявлять неработающими на сервере: прикладные HTTPS-запросы через них прошли. Это не устанавливает причину отказов на Android или в конкретном регионе. Оснований менять ключи, certificate pins, transport или перезапускать runtime по собранным данным нет.

## Источники и границы публикации

| ID | Источник | Назначение |
|---|---|---|
| S1 | [AGENTS.md](../../AGENTS.md), [SECURITY.md](../../SECURITY.md), [README](../../README.md), [протокол](../EXPERIMENT_PROTOCOL.md) на указанном main | Канон, разрешения, критерии evidence |
| S2 | Приватный `LILFOX_AM_FULL_HANDOFF_2026-10-06.md`, modified 2026-10-14 20:24:55 UTC, §§20.30–20.37 | Последний handoff, исторические пробы и receipt адресной правки |
| S3 | Два публичных DoH resolver и облачные HTTPS probes, 21:45 UTC | Текущий DNS и границы управляемого облачного proxy |
| S4 | Desktop Commander → существующий WSL → прежний pinned SSH, 21:57–22:14 UTC | Текущее состояние именно Amsterdam |
| S5 | Ограниченные Windows/WSL network probes и серверные observers | Текущий data path и локализация наблюдаемых отказов |
| S6 | [Генератор](../../scripts/lilfox-family-bundle.py) и [тесты](../../tests/test_lilfox_family_bundle.py) | Независимость delivery origin и VPN destination |

`FACT` — [ранний публичный deployment checkpoint](LILFOX-AM-DEPLOYMENT-CHECKPOINT-2026-10-04.md) старее S2/S4 и не подменяет их. Старые разрешения на установку/исправление не использовались.

`DECISION` — здесь нет рабочих IP/hostnames/ports, SNI, fingerprints, recipient identifiers, приватных URL, credentials, конфигов, raw logs или packet dumps. `OLD_ADDRESS`, `CURRENT_ADDRESS`, `DELIVERY_HOST`, `LEGACY_CERT_HOST` обозначают роли из приватного inventory. Ссылки на приватные источники не публикуются.

## Архитектура и текущий сервер

`FACT` — Amsterdam — отдельный сервер: I — отдельный Xray VLESS RAW/TCP REALITY/Vision; II — отдельный Xray VLESS XHTTP REALITY; III — Hysteria2 TLS/QUIC/UDP. Отдельный Caddy доставляет статические персональные Landing/subscription. Семь серверных identities включают владельца и шесть получателей; один VPS остаётся общим failure domain.

`FACT` — S6 строит delivery URL из `public_base`, а destination трёх профилей из отдельного `host`. HTML сохраняет subscription URL в metadata. DNS, распространённая source URL, HTML metadata, server subscription destination и уже импортированный Happ profile — разные состояния; изменение одного не обновляет остальные.

`FACT` — после запуска Desktop Commander прежняя блокировка снята. Найдены существующие WSL identity и target-specific known_hosts с permissions 0600; прежний alias содержит ровно одну ED25519 pin. SSH прошёл с `StrictHostKeyChecking=yes`, `UpdateHostKeys=no`, `BatchMode=yes`, explicit identity/known_hosts, отключёнными forwarding и global known_hosts. Использован ранее документированный HostKeyAlias после замены адреса. TOFU и обновление доверия не выполнялись.

`FACT` — проверена Ubuntu 24.04; все четыре units active/running, NRestarts=0. Ожидаемые TCP/UDP listeners принадлежат MainPID нужных units. После диагностики все четыре PID сохранились. Пути runtime config I/II/III совпадают с ожидаемыми, disk config не новее запуска процесса. Это не чтение runtime keys из памяти.

`FACT` — I/II JSON разобраны: по одному VLESS inbound и семь clients, ожидаемые transport/security/ports. III YAML разобран с проверкой duplicate keys: дублей нет, семь userpass entries, ожидаемый UDP listener. Свободное место превышает 1 GiB и 10%; дисковое переполнение не обнаружено.

`FACT` — все шесть subscriptions содержат по три профиля. Для 18 профилей destination совпадает с CURRENT_ADDRESS, прежний отсутствует. Для 12 VLESS profiles auth/flow/transport/SNI-membership/Short-ID-membership совпали; public keys вычислены из серверных private keys внутри VPS и сравнения true. Все шесть XHTTP paths совпадают с сервером. Для шести III auth и pin фактического certificate совпали. Значения не выводились.

`FACT` — III certificate находится в пределах notBefore/notAfter. Caddy config успешно адаптируется, содержит ожидаемый static root и оба delivery hostnames. С localhost VPS HTTPS с нормальной CA/hostname validation прошёл для обоих имён; Caddy certificates действуют до января 2027. Это origin TLS evidence, независимое от облачной TLS interception.

## Персональная доставка

`FACT` — на сервере ровно шесть Landing и шесть subscription files, symlinks не обнаружены. Все 12 точных путей проверены локально через Caddy с полноценным TLS. HTTP200, Content-Length и полный streaming SHA-256 совпали с диском. У subscriptions по три профиля, text/plain, ожидаемый profile-title и Cache-Control no-store; у Landing также no-store.

`FACT` — HTMLParser обнаружил ровно одну subscription meta в каждой странице. Три origin — DELIVERY_HOST, три — LEGACY_CERT_HOST; все шесть ссылок сопоставились с существующими subscription files. После исправления только собственного DNS половина Landing продолжит предлагать legacy source URL.

`FACT` — legacy hostname кодирует OLD_ADDRESS и по текущему DNS остаётся на нём. Правка другой A-записи его не перенаправит. Какие source URLs сохранены в шести телефонах, не проверено.

`FACT` — существующий локальный операторский пакет содержит только три уникальные Landing URL и три subscription URL, все на собственном домене; его нельзя выдавать за полную текущую шестёрку. Для проверки серверной шестёрки использованы фактические текущие filenames/metadata, без угадывания tokens. Чувствительные данные обрабатывались в памяти VPS/ноутбука, без передачи значений в чат или GitHub.

`FACT` — первые bounded prefix reads не подтверждали целостность больших HTML: страницы существенно больше установленного prefix limit. Это ограничение harness, а не corruption. Один исправленный streaming hash check подтвердил полные bodies всех 12 файлов. Ошибка экранирования в первоначальном диагностическом regex metadata исправлена заменой на HTMLParser; его отрицательный результат не использован как серверная ошибка.

## DNS, внешний путь и проверка I/II

`FACT` — по одному A/AAAA запросу к Google и Cloudflare для двух hostname: оба A выбирают OLD_ADDRESS; AAAA пусты, rcode=0. Для собственного hostname TTL=300. Это resolver evidence, не чтение DNS control plane или доказательство текущего владения OLD_ADDRESS.

`FACT` — в облаке normal root HTTPS обоих hostname дал proxy HTTP502. Принудительный CONNECT на CURRENT_ADDRESS при сохранении Host/SNI дал Caddy HTTP404. Cloud curl увидел issuer OpenAI/openai.com: ssl_verify_result=0 там не проверяет origin certificate. Прямой облачный TCP недоступен также к независимому control; этот runtime не используется как raw VPN/UDP-клиент.

`FACT` — Windows native TCP probes открыли ожидаемые SSH/I/II/delivery endpoints; синхронный серверный observer увидел входящие SYN, включая SSH positive control. Этот тест не отправлял REALITY или HTTPS payload и не является PASS VPN/доставки.

`FACT` — WSL HTTPS root при explicit CURRENT_ADDRESS для обоих Host/SNI timeout. Первая внешняя персональная HTTPS-проба в WSL остановлена на timeout. Windows Node с explicit CURRENT_ADDRESS, origin SNI и обязательной TLS verification также timeout до получения первого Landing. Перебора приватных путей и отключения проверки сертификата не было.

`FACT` — один различающий Windows curl root request с explicit CURRENT_ADDRESS: exit28, HTTP0, body0. За синхронное 35-second READY-окно серверный observer не увидел ни одного входящего/исходящего пакета delivery endpoint; одновременно наблюдал encrypted SSH payload. Отказ этой пробы произошёл до наблюдаемого target listener, а не вследствие выдачи Caddy ошибочного тела/сертификата. Точный upstream/local hop не установлен; отсутствие пакетов в одном окне не доказывает конкретного виновника.

`FACT` — на Windows включён loopback system proxy, а выбранный IP route имеет tunnel-named interface. В проверенной выборке application-specific Windows Firewall rules для участвующих executables явных правил не найдено; это не исключает WFP/third-party policy. Из active Xray command line доступный disk-config не извлечён; фактические sniffing/routeOnly/rules не прочитаны. Нельзя объявлять причиной конкретный Happ setting или считать путь прямым RF-интернетом.

`HYPOTHESIS` — source/application routing, tunnel interception, SNI destination override либо фильтрация внешнего пути могут объяснять различие empty TCP и full request. Участие российского оператора, entire-prefix block, MTU или дефект Caddy не установлены. Эти гипотезы не являются основанием менять production routing или протокол.

`FACT` — отдельные нативные Windows Xray 26.7.28 I и II использовали точные текущие server subscriptions. Конфигурации переданы через stdin, config test exit0, SOCKS bound только loopback, sniffing тестового inbound выключен. Системный TUN/proxy/default route и рабочий client process не изменялись.

| Проба | UTC | HTTPS endpoint 1 | HTTPS endpoint 2 | Exit-IP match | Cleanup |
|---|---|---|---|---|---|
| I, один candidate | 22:10:45 | HTTP200, body>0 | HTTP200, body>0 | true для обоих | Собственный тестовый PID завершён, исходные Xray PID сохранены |
| II, один candidate | 22:12:04 | HTTP200, body>0 | HTTP200, body>0 | true для обоих | Собственный тестовый PID завершён, исходные Xray PID сохранены |

`FACT` — использованы два независимых HTTPS exit services, нормальная TLS verification и SOCKS hostname resolution; в прикладном выводе только boolean IP match. Для I READY observer также зарегистрировал входящий трафик точного destination listener. Общие outgoing counters не используются: такой capture может включать TLS-cover egress. Observers ограничены timeout, завершились; raw packet contents не сохранялись и не публиковались.

`FACT` — `BASIC_HTTPS_EXIT=PASS` относится к одному candidate каждого I/II в текущем контуре ноутбука, где management TUN/proxy оставался включён. Нет трёх reconnect repetitions, HTTP acceptance, прямого RF/mobile comparison или restart/isolation tests. Это не formal G2/G3, не 18/18 и не доказательство восстановления Happ. Независимый нативный III client в проверенном каталоге существующего Happ core не найден; установка запрещена, III client test не подменён старой WSL timeout-пробой.

## Минимальный change packet — НЕ ПРИМЕНЁН

`DECISION` — следующие gates независимы и требуют отдельного разрешения владельца. Секретные IDs/allowlists/hashes агент подставляет из разрешённого приватного inventory; владелец не должен переносить их вручную. DNS control-plane IDs/snapshot пока недоступны, поэтому исполняемый DNS-пакет ещё не готов. Новые серверные protocol changes не предлагаются.

### G0 — обязательный preflight перед любой записью

- `TODO` — повторно проверить прежнюю SSH pin, target identity, текущий provider assignment и неизменность затрагиваемых объектов. Host-key mismatch/нет pin — STOP без TOFU.
- `TODO` — получить DNS control-plane read: ровно одна ожидаемая A, record/zone IDs, TTL и DNS-only status. Resolver TTL не заменяет control-plane snapshot.
- `TODO` — сохранить приватный allowlist трёх legacy-meta files с original hashes и одно-единственное разрешённое преобразование authority; отдельно hashes шести subscription files и route/Caddy configs как protected set.
- `TODO` — предварительно проверить безопасный rollback. OLD_ADDRESS после provider replacement может больше не принадлежать владельцу. Snapshot не делает возврат на него безопасным. Если безопасного возврата нет — gate остаётся закрытым до отдельного согласованного recovery/roll-forward плана.

### G1 — одна DNS A-запись

- `TODO` — цель: DELIVERY_HOST A, `OLD_ADDRESS -> CURRENT_ADDRESS`. Ни одной другой записи/параметра не менять.
- `TODO` — будущий API shape: `PATCH /zones/{verified_zone_id}/dns_records/{verified_record_id}`, payload содержит только `content=CURRENT_ADDRESS`. Непосредственно перед PATCH повторить GET и сравнить original type/name/content/ttl/proxied с snapshot. Compare-before-write не атомарный CAS: при параллельном редактировании — STOP.
- `TODO` — backup: приватный snapshot полной одной DNS-записи с временем, IDs и permissions 0600, вне Git/VPS public root. Provider assignment CURRENT_ADDRESS подтверждён до применения.
- `TODO` — Expected: меняется только content; TTL/proxy status сохранены. Readback control plane точен, затем оба resolver после прежнего TTL/распространения выбирают CURRENT_ADDRESS.
- `TODO` — rollback: вернуть original content только после подтверждения владения и безопасной выдачи на прежнем адресе; иначе gate закрыт по G0. Не откатывать вслепую.
- `TODO` — PASS: точный DNS readback и два согласованных resolver. Отдельно проверить real HTTPS delivery; DNS PASS не равен restoration PASS.
- `TODO` — риск низкий для изолированной записи, но прежний чужой адрес и stale caches создают риск неверного destination. Ошибка сверки, multiple/unexpected records или неподтверждённый rollback — STOP.

### G2 — только три legacy metadata authority

- `TODO` — после DNS gate изменить в ровно трёх текущих Landing единственный subscription meta origin: LEGACY_CERT_HOST authority -> уже существующий DELIVERY_HOST authority. Сохранить HTTPS scheme, port, private path/token, query/fragment, body/assets и все auth/pins; остальные три Landing и шесть subscriptions не менять.
- `TODO` — exact scope до apply: HTMLParser подтверждает 6/6 metadata, split 3+3; каждый source path — regular non-symlink file в ожидаемом root с original hash. Частная allowlist фиксируется до записи. Любое расхождение — STOP.
- `TODO` — backup: только три исходных файла с hashes/permissions/ownership в отдельном приватном 0700 каталоге вне web root/Git; достаточное место и readback проверены.
- `TODO` — publication: подготовить три candidates в приватном временном каталоге на той же FS вне web root; проверить единственную разрешённую замену, metadata/path и protected hashes. Публиковать каждый независимый recipient file атомарным file replace после повторной сверки original hash и сохранения mode/owner. Не удалять/заменять существующий public каталог, не запускать генератор поверх него, не оставлять temp files в web root. Общая трёхфайловая операция не является одной атомарной транзакцией; receipt учитывает каждый опубликованный файл.
- `TODO` — Expected: 6/6 Landing metadata используют собственный origin; tokenized paths и 18 profiles неизменны. Static Caddy reload/restart не нужен и не разрешён.
- `TODO` — rollback: восстановление только фактически затронутых файлов по receipt с hash readback и проверкой protected set. Восстановление legacy links допустимо лишь при безопасном destination; иначе gate закрыт по G0. Чужие файлы не удалять.
- `TODO` — PASS: полные шесть Landing и шесть subscription fetches через новый DNS, настоящая origin TLS verification, правильный recipient correspondence, по три профиля, 18 current destinations, отсутствие изменения protected files. Затем фактический refresh Happ. Риск средний: меняется доставка трём получателям.
- `TODO` — уже сохранённые в Happ legacy source URLs не обновятся от правки HTML. Нужны точная сверка source URL и безопасная повторная передача текущего приватного подключения; credentials не регенерировать автоматически.

### G3 — остаточный внешний delivery path и клиентская приёмка

`TODO` — до объявления восстановления различить текущий TUN/proxy path и прямую целевую сеть одним согласованным независимым клиентским тестом с source/time и ingress observer. Не отключать рабочий management VPN без отдельного разрешения. Сначала проверить фактические active routing/sniffing flags, если появится разрешённый доступ к ним; их значения не угадывать.

`TODO` — если direct delivery при правильных DNS/origin всё ещё не достигает VPS, готовить отдельный пакет только по доказанному network/front-door дефекту. Сейчас нет основания переносить порты, устанавливать новый tunnel/VPN, менять firewall, сертификаты или REALITY. Риск таких предполагаемых изменений выше DNS/meta-правок; они не входят в этот пакет.

`TODO` — III проверить существующим независимым UDP/QUIC-клиентом, когда такой контур доступен. Затем шесть Happ subscriptions × I/II/III, точная identity/source, DNS, HTTP/HTTPS, два exit-IP checks и три clean reconnects в целевых mobile/Wi-Fi сетях. Restart/isolation acceptance требует отдельного будущего разрешения; нынешний запрет действует. Без недостающих проверок verdict PARTIAL.

## Безопасность, валидация и STOP

- `FACT` — перед публикацией отчёта ранее прошли существующие 26 generator tests. Это не live VPN acceptance.
- `FACT` — диагностические commands не записывали VPS configs/subscriptions/DNS/trust и не перезапускали units; после проб все четыре units сохранили PID/NRestarts. На Windows временные client configs были только в памяти, собственные процессы завершены, рабочие Xray PID сохранены. Новое ПО не устанавливалось.
- `FACT` — Primary DeepWork и PP-LAB-01 не использовались как targets/control hosts; payment/deployment/merge отсутствуют.
- `TODO` — результаты staged/full-diff Gitleaks, manual sanitization, GitHub readback и CI для этой редакции фиксируются в существующем Draft PR. Нельзя считать прежний CI проверкой нового commit.
- `TODO` — не проверены Android/прямые RF-сети, реальные source URLs шести телефонов, III UDP data path и formal acceptance. Конкретная причина loss до delivery listener и доступ к DNS control plane остаются ограничениями.
- `DECISION` — после этого read-only этапа любые изменения STOP до отдельного разрешения. Ближайший полезный шаг — завершить приватные DNS snapshot/rollback prerequisites и согласовать G1/G2, сохраняя отдельную проверку внешнего пути.
