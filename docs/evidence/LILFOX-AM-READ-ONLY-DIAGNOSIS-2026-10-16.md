# LilFox Amsterdam — read-only diagnosis и пакет восстановления

`FACT` — последнее продолжение **AMSTERDAM-G0 / Cloudflare UI Recovery**, 16 октября, 13:04–13:06 UTC: штатный UI однозначно выбирает одну целевую A-запись и открывает отдельную редактируемую форму. Все отображаемые поля сверены до и после read-only reload. **UI-G1 подготовлен для отдельного утверждения без API record_id**; сохранение/изменение полей не выполнялось. `UI_G1_PROCEDURE=READY_FOR_REVIEW`, `UI_G1_WRITE=NOT_RUN`, `G0_PASS=NOT_DECLARED`, `EXECUTION_AUTHORIZED=false`. Последняя процедура — в секции «UI-G1»; прежний API blocker остаётся ограничением API-варианта. Backup и ночная диагностика не повторялись.

- `FACT` — Evidence ID: `LILFOX-AM-READ-ONLY-2026-10-16`; отчёт обновлён после подключения Desktop Commander.
- `FACT` — основные сетевые и серверные наблюдения: 15 октября 2026, 21:45–22:14 UTC (16 октября, 00:45–01:14 МСК).
- `FACT` — исходный main: `8b29c9cff517c0b114a4aee8f6f4745fa94411c3`.
- `DECISION` — разрешены диагностика, этот документ в рабочей ветке/Draft PR и, по новому поручению, долговечный backup только в существующем приватном операторском WSL-пространстве. Изменения VPS/DNS/действующих подписок, SSH trust, deployment и merge не разрешены.
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

## AMSTERDAM-G0 — исторический checkpoint 16 октября утром и проект G1/G2

`FACT` — статусы доступа/backup в этой секции относятся к 06:49–07:01 UTC. Позднее разрешение на приватный backup и результаты авторизованной панели приведены в «Завершение G0»; прежний sign-in blocker больше не актуален.

`FACT` — G0 наблюдения 06:49–07:01 UTC. Main и Draft PR №15 не изменились с предыдущего этапа. Приватный handoff по-прежнему modified 2026-10-14 20:24:55 UTC. Клиентские I/II, полный Caddy delivery и III acceptance повторно не запускались.

`DECISION` — прежний черновой пакет в этом месте заменён настоящей редакцией. Владелец подтвердил: OLD_ADDRESS больше не наш. Обратный DNS rollback и возврат активных legacy URL запрещены; копия старого состояния не является разрешением снова направлять на него пользователей.

`FACT` — итог подготовки: `AMSTERDAM_G0=PARTIAL_STOP`, `EXECUTION_READY=false`. Данные DNS control plane не получены, постоянная резервная копия трёх HTML не создана. Пакет описан и проверен в доступном read-only объёме, но ещё не готов к разрешению production-записи одним решением.

### Новые доказательства и конкретные блокеры

| Проверка | Actual |
|---|---|
| Свежие A/AAAA, Google + Cloudflare | DELIVERY_HOST A → OLD_ADDRESS, TTL=300; LEGACY_CERT_HOST A → OLD_ADDRESS, TTL=3600; AAAA пусты у обоих |
| NS/SOA зоны | Cloudflare authoritative names обнаружены; идентификаторы аккаунта/зоны/записи из публичного DNS не получены |
| Read-only panel | Подключённый Chrome открыл Cloudflare sign-in; DNS records page не доступна в этой сессии |
| Идентификаторы и параметры записи | zone_id=NOT_READ, record_id=NOT_READ, control-plane TTL=NOT_READ, proxied=NOT_READ |
| Существующий CLI/API-контур | В проверенных Windows/WSL env нет доступного CF token/key; Wrangler executable не найден; четыре проверенных Windows config locations не содержат default config. Это ограниченный поиск, а не утверждение об отсутствии credentials во всём компьютере |
| Desktop Commander / SSH | После краткого разрыва DC Online; прежняя pin/identity найдены, все G0 SSH-запросы прошли strict trust без TOFU/обновления ключей |
| Текущий адрес сервера | CURRENT_ADDRESS присутствует на interface pinned target; OLD_ADDRESS на interfaces отсутствует |
| Static staging prerequisites | Каталог вне public root на той же FS возможен; свободно больше 64 MiB. Stage/backup directories не создавались |
| Старый address-fix snapshot | Существует; references: 6 subscription files, 0 HTML. Для G2 это не резервная копия трёх текущих Landing |

`FACT` — значения IDs/TTL/proxy нельзя подменять догадкой из DNS-only handoff. Cloudflare sign-in не завершался; новые credentials, OAuth grants, keyring access и установки не создавались. Панель оставлена для продолжения входа; cookies/токены браузера не извлекались.

`FACT` — доступные самостоятельные read-only пути к панели/CLI проверены; authenticated DNS read — текущий blocker. Подбор IDs, перенос браузерных cookies, массовый поиск секретов и переключение на другую сессию ради обхода входа не выполнялись.

### Точная allowlist без персональных URL

`FACT` — на текущем pinned target шесть страниц, ровно одна metadata в каждой; legacy origin только в **slots 2, 5, 6**. Slot — 1-based позиция в лексикографически отсортированном списке текущих `page/*.html`; это не имя получателя и не файл для угадывания.

`FACT` — точный состав связан с содержимым/путями/правами, а не только с порядковым номером:

| Guard | SHA-256 |
|---|---|
| Все шесть текущих страниц и их metadata роли | `61a36ceb21976cb1201b14681e9f7c79182302e8067bca2124802085d10bc251` |
| Protected set: шесть subscriptions + Caddy config + configs I/II/III | `7f517d021fc6189b1b4b47e52c38a18c8c256c599a2a9c89cf841808231f08c1` |

`DECISION` — digest не является файлом backup или working token. Приватные paths/URL и сами source bytes в публичный документ не включены. Перед исполнением агент восстанавливает allowlist из pinned source и обязан получить те же digests. При drift — STOP, а не автоматическая замена эталона.

`FACT` — алгоритм page manifest: для шести файлов в указанном порядке формируются объекты с ключами `slot, role, file, sha256, size, mode, uid, gid, nlink`; `file` — исходный абсолютный private path, role — `owned|legacy`, sha256 — исходные bytes, mode — `stat.S_IMODE`. Hash от UTF-8 `json.dumps(rows, sort_keys=True, separators=(',', ':'))`. Protected manifest: sorted subscription files, затем Caddy, затем I/II/III; поля `file,sha256,mode,uid,gid`, mode = mode bits & 0777; та же сериализация.

`FACT` — все три source files regular, non-symlink, nlink=1. Все шесть metadata ссылаются на существующие локальные subscription files; новые назначения не придумывались.

### Проверенные candidates и резервирование

`FACT` — в RAM VPS подготовлены ровно три candidates. В каждом заменяется только authority subscription meta: LEGACY_CERT_HOST -> DELIVERY_HOST при сохранении HTTPS и исходного port. HTMLParser проверил один meta; source tag однозначен. Сохранены path/token, query, fragment и все bytes вне единственного meta tag; обратная byte-substitution возвращает исходник. Изменения не публиковались.

`FACT` — исходные три HTML суммарно 8 122 223 bytes. In-memory tar.gz — 5 924 601 bytes, ровно три regular `page/<original-name>` entries с mode/uid/gid. Полный readback каждого member совпал SHA-256 с исходником. Это `BACKUP_ROUNDTRIP_DRY_RUN=PASS`, **не durable backup**: bytes не экспортировались, archive не сохранялся и после процесса не доступен для восстановления.

`FACT` — существующий серверный backup каталог проверен без symlink traversal и без распаковки в FS: один snapshot, нет подходящих HTML/archive copies. Snapshot адресной правки не содержит HTML references. Независимая восстановимая копия трёх Landing пока отсутствует.

`DECISION` — текущая миссия read-only и разрешает изменения только документации. Новые постоянные backup/candidate files на VPS/Windows не записывались. Поэтому полное требование «подготовлены проверенные резервные копии» ещё не выполнено; dry-run не переименовывается в backup PASS.

`TODO` — до production writes следующего разрешённого run создать off-VPS backup в существующем приватном operator workspace WSL, не в public root/репозитории/общих источниках и не на общем NTFS-каталоге без эквивалентных ACL. Новая директория 0700 через exclusive create; archive/manifest 0600, без overwrite. Сохранить только три HTML и один target DNS-record snapshot; private SSH keys и route credentials не копировать. Записать fsync, прочитать архив заново с диска и проверить ровно три разрешённых regular members, hashes, mode/uid/gid; path traversal/symlink/hardlink entries запрещены. Свежий target readback должен совпасть с frozen page/protected manifests. Без этого ни G1, ни G2 не стартуют.

### Исполнительный порядок после закрытия G0 и отдельного разрешения

`DECISION` — сейчас никакие перечисленные ниже writes не выполнялись. Одно будущее разрешение может покрыть тесно связанный recovery run с checkpoints: проверенный backup → G1 → readback → G2 → readback, с остановкой на первом неожиданном результате. Оно не покрывает другие записи, протоколы, новые credentials, services или targets.

#### G1 — ровно одна A-запись

1. `TODO` — authenticated read только нужной зоны и точного DELIVERY_HOST: `GET /zones?name=ZONE`, затем `GET /zones/{zone_id}/dns_records?name=DELIVERY_HOST` и details выбранного record_id. Проверить аккаунт/зону, ровно одну ожидаемую A, отсутствие конфликтующего CNAME/AAAA на этом имени, исходный OLD_ADDRESS и `proxied=false`. Иное состояние — STOP и пересмотр packet, не исправление соседних records.
2. `TODO` — сохранить read-only snapshot конкретной записи: IDs, type/name/content/ttl/proxied и остальные business fields; без Authorization/cookies. Не экспортировать всю зону с другими проектами. TTL брать из control plane, не из resolver cache.
3. `TODO` — непосредственно перед write повторить GET и сравнить business fields/IDs с snapshot. Не называть compare-before-write атомарным CAS. При конкурирующей правке — STOP.
4. `TODO` — один `PATCH /zones/{verified_zone_id}/dns_records/{verified_record_id}`. Согласно [актуальному Cloudflare API](https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/edit/), сформировать A payload с исходными обязательными полями, изменяя по смыслу только content:

```text
type    = before.type        # must be A
name    = before.name        # exact DELIVERY_HOST
ttl     = before.ttl         # not inferred from public DNS
proxied = before.proxied     # must remain false
content = CURRENT_ADDRESS   # only intended semantic delta
```

`DECISION` — это уточняет прежний черновик «payload только content»: API schema описывает также name/ttl/type. Не использовать PUT, bulk/batch update, delete/recreate, смену proxy status или TTL. IDs/значения агент подставляет из проверенного snapshot, не просит владельца переносить их вручную.

5. `TODO` — details readback: content текущий; IDs/name/type/ttl/proxied/comment/tags/settings и остальные protected business fields прежние. Изменение серверных timestamps как API bookkeeping не считать изменением бизнес-параметров. При write timeout выполнить один различающий GET; неизвестный outcome — STOP, не повторять PATCH вслепую.
6. `TODO` — оба resolver должны выбрать CURRENT_ADDRESS после cache expiry; интервалы наблюдения не длиннее 60 секунд, конечный deadline — два исходных TTL + 60 секунд, максимум 10 минут для этой операции. При большем control-plane TTL — заранее пересмотреть окно, не ждать бесконечно. Далее выполнить bounded TLS/delivery verification; не очищать global DNS/cache и не переключать management VPN.

`TODO` — риск: некорректный record scope, cache propagation и конкурирующая правка. Поле proxied не переключается. PASS G1 — точный control-plane readback и два resolver, а не работа VPN.

#### G2 — только metadata трёх зафиксированных страниц

1. `TODO` — G1 должен подтвердить безопасный текущий DNS destination; fresh pinned source должен совпасть с обоими frozen digests. Backup readback обязан пройти до любого production write.
2. `TODO` — подготовить точно проверенное RAM-преобразование в приватном 0700 stage вне public root на той же VPS FS. Candidates создаются эксклюзивно, без shell URI arguments. Не сериализовать заново весь HTML; заменить только raw content attribute единственного meta tag. Сохранить исходные mode/owner после подготовки и до публикации.
3. `TODO` — проверить 3 candidates: единственная authority substitution, path/token/query/fragment/scheme/port неизменны, HTML outside tag прежний, никаких новых file targets. Проверить protected set и safe parent directories.
4. `TODO` — последовательно публиковать каждый файл атомарным file replace, используя private allowlist, directory handles/no-follow и повторный source hash/nlink/owner check. Не заменять каталог, не удалять чужие файлы и не запускать generator поверх public root. После каждого replace — readback hash и приватный receipt по конкретному файлу. Три замены не являются одной атомарной транзакцией.
5. `TODO` — readback: 6/6 metadata на собственном origin, 6 subscriptions и route/Caddy configs имеют прежний protected digest. Все 12 точных путей должны проходить полное body/hash/TLS сравнение на origin. Никаких restart/reload, certificate changes, credential changes или subscription regeneration.
6. `TODO` — настоящую внешнюю доставку и Happ refresh проверить отдельно. Уже сохранённый в телефоне legacy source URL не обновляется от HTML; его exact identity надо сверить прежде, чем обещать восстановление.

`TODO` — риск средний: три пользователя могут временно получить непригодный Landing, а операция не глобально атомарна. Stop до следующего файла при любой ошибке; ранее опубликованные результаты не откатывать на чужой origin.

### Безопасное аварийное восстановление без OLD_ADDRESS

`DECISION` — обычный inverse rollback невозможен: OLD_ADDRESS не наш. Требуется отдельное принятие владельцем следующей forward-only recovery policy в разрешении будущего G1/G2; нынешняя read-only миссия её не авторизует. Без принятой policy write gate закрыт.

| Сбой | Предлагаемое безопасное действие в будущем run |
|---|---|
| Нет проверенного durable backup / manifest drift / SSH pin mismatch | Никаких writes; STOP |
| G1 не отправлен или отклонён API | Не переходить к G2; STOP, не менять другие records |
| G1 timeout, outcome неизвестен | Один GET. Если результат неизвестен — STOP без повторов |
| G1 A уже подтверждён на нашем CURRENT_ADDRESS, но external HTTPS FAIL | Оставить безопасное новое A, сохранить evidence и STOP внешнего path. Не возвращать старый IP и не удалять запись из-за одного network failure |
| G1 неожиданно изменил другие поля / конкурентная правка | STOP, сохранить snapshot/readback; никаких автоматических чужих-field overwrite/delete |
| G2 source drift / ошибка подготовки | Не публиковать новый файл, сохранить ранее подтверждённые безопасные результаты; STOP |
| Уже опубликованный G2 HTML повреждён и его hash равен receipt этого run | Восстановить из проверенного backup **с повторно внесённым owned authority** в RAM; проверить frozen original + точный candidate hash, затем атомарно опубликовать только этот файл |
| Исправленный безопасный candidate не удаётся восстановить | Только если заранее включено в разрешение: атомарный maintenance HTML без JavaScript, ссылок, redirect и personal data в том же allowlisted файле; временный отказ выдачи, не перенаправление на OLD_ADDRESS. Если fallback не разрешён — STOP без дополнительных writes |
| Исходный backup содержит legacy URL | Использовать как архивный source для ремонта, никогда не публиковать его bytes вслепую |

`DECISION` — DNS DELETE/recreate, rollback на OLD_ADDRESS, изменение других zone records и автоматический перенос на другой сервер в пакет не входят. Физический backup сохраняет прежнее состояние для проверки/ремонта, но не делает прежний destination безопасным.

`TODO` — до production approval предъявить владельцу завершённый private DNS snapshot с IDs/TTL/proxy, подтверждение durable backup и точную safety policy. Сейчас эти prerequisites не все выполнены, поэтому `READY_FOR_ONE_OWNER_DECISION=false`.

### Независимые оставшиеся задачи

`FACT` — внешний HTTPS отказ до наблюдаемого listener и III UDP/QUIC acceptance не устранены и не переобозначены как DNS/meta defects. G0 не повторял ночные client tests. Ночные I/II HTTPS successes относятся к тогдашней Windows TUN/proxy среде; они не становятся сегодняшним Android PASS.

`TODO` — после G1/G2 провести независимый реальный Happ refresh и целевую клиентскую матрицу. При остающемся network failure — один различающий read-only test с source/time/control, затем STOP направления; не менять протоколы, ports, firewall, certificate pins или рабочую маршрутизацию на догадке. III требует отдельного существующего UDP/QUIC-клиента; установки и рестарты по-прежнему запрещены.

## Завершение G0 — 16 октября, 12:40–12:51 UTC

`DECISION` — продолжение от `4b16778a`, без повторного запуска ночной диагностики. Новый scope явно разрешает приватный backup и безопасные тесты. Production writes по-прежнему запрещены. Этот checkpoint уточняет предыдущий, но не превращает частичную подготовку в G0 PASS.

### Авторизованный DNS read: что получено и что блокирует DONE

| Параметр | Actual / происхождение |
|---|---|
| Аккаунт/зона | Авторизованная существующая Chrome-сессия; account_id и zone_id прочитаны из видимой панели Overview; точные значения оставлены только в приватном backup snapshot |
| Целевое имя/type/content | В Records после поиска точного имени одна A-запись, content=OLD_ADDRESS; конфликтующие записи того же имени в показанном результате отсутствуют |
| Proxy | DNS only; у switch `aria-checked=false`, то есть `proxied=false` |
| TTL control plane | Видимый selector Auto, связанное DOM-поле имеет value `1`. Это Auto sentinel, не одна секунда |
| Фактический TTL | Auto для DNS-only = 300 секунд по [Cloudflare TTL reference](https://developers.cloudflare.com/dns/manage-dns-records/reference/ttl/); свежие Google и Cloudflare DoH также вернули OLD_ADDRESS с TTL=300, rcode=0 |
| Comment | Record Attributes раскрыты read-only; поле пустое |
| record_id / остальные API business fields | `NOT_READ`: раскрытый record, его DOM attributes/links и Record actions не показывают record_id; полного JSON из API нет |
| Запись в панель | Не выполнялась: поля записи не заполнялись, Save оставался disabled, раскрытие закрыто Cancel; финальный readback A/DNS only/Auto прежний |

`FACT` — профильный DNS connector среди доступных инструментов не обнаружен. Прежний ограниченный CLI/env check не дал существующего API credential. Дополнительно выполнен ровно один read-only переход браузера к точному same-origin API collection выбранной зоны с фильтром имени: клиент браузера отказал `ERR_BLOCKED_BY_CLIENT`. API-ответ не получен, record_id не установлен. Повторов, обхода блокировки, переноса cookies, чтения токенов, скрытого состояния приложения и создания credentials не было.

`DECISION` — account_id, zone_id и UI component IDs не подменяют record_id. TTL/public DNS не дают API identity. Общий export зоны не выполнялся, чтобы не копировать другие ресурсы. Обычные права авторизованного аккаунта не являются техническим read-only ACL; read-only здесь обеспечен выполненными действиями.

`TODO` — точный оставшийся blocker: безопасный существующий authenticated GET целевой DNS-записи, возвращающий её record_id и все business fields. Достаточен разрешённый профильный API/connector либо официальный read-only UI, показывающий эти параметры. Новые credentials, расширение доступа и обход ограничения клиента не входят в эту миссию. До получения данных действуют `DNS_SNAPSHOT_COMPLETE=false` и STOP G1/G2.

### Durable backup и независимый тест восстановления

`FACT` — в существующем target-specific private operator workspace WSL создан exclusive каталог `amsterdam-g0-backup-20261016T124743Z-85bf25ad`. Абсолютный путь, filenames получателей и URL не публикуются. Каталог не находится в Git/public root/общих источниках. Проверены все parent components: root-owned, без symlink и group/other write; внешний root и target private root 0700.

`FACT` — VPS только читал исходники и собирал archive в RAM. Bytes переданы существующим strict-pinned SSH в RAM операторского WSL и записаны только в разрешённое private backup space. SSH keys, route configs и credentials в архив не копировались. В Git/чат/cloud workspace HTML/архив не передавались. Замены опубликованных файлов, записи backup на VPS и изменения SSH trust отсутствуют.

| Проверка | Actual |
|---|---|
| Allowlist | Ровно slots 2/5/6, каждый regular/non-symlink, nlink=1; исходный page digest совпал с frozen guard |
| Состав | `html-originals.tar.gz`: ровно три regular `page/<original-name>` members; исходные mode/uid/gid/size сохранены в архиве и приватном manifest |
| Размер | 5 924 601 bytes archive; исходные HTML суммарно 8 122 223 bytes |
| Archive SHA-256 | `320f2db063ed828fddd5b1ba9b20a8d3d76b2d83205c3ce088629614ecafbd55` |
| Private manifest SHA-256 | `54c28a3ec33149d49fe8325294d7b03d42f953adb7db1de4d6d06d4b3e25d101` |
| Доступ и запись | Run/restore-check dirs 0700; archive/manifest/receipts/restore-check files 0600, root-owned, nlink=1; O_EXCL/O_NOFOLLOW, flush+fsync файлов и directories |
| Полнота и безопасность архива | 3/3 полных hashes и исходные mode/uid/gid/size совпали; absolute/parent traversal paths, symlink/hardlink и лишние members запрещены |
| Восстановление | Три member прочитаны с диска и явно записаны эксклюзивно в private restore-check files; 3/3 повторных SHA-256 совпали с исходниками; приватные копии оставлены 0600, исходные mode/owner доступны в archive/manifest |
| Отказоустойчивость проверки | Обрезанная в RAM копия архива отвергнута; повреждённый архив не записывался на диск и не использовался для восстановления |
| Долговечность относительно процесса | После завершения создающего процесса отдельный новый WSL/SSH process снова прочитал archive/manifest/restore-check с диска; все hashes/permissions/members PASS |
| DNS observation | Отдельный private JSON содержит только полученные target UI параметры и IDs, без auth headers/cookies/tokens; явно `complete=false`, record_id и прочие API поля null |

`FACT` — `HTML_DURABLE_BACKUP=PASS`, `RESTORE_CHECK=3/3 PASS`. Это постоянная off-VPS копия на операторском диске; она не является независимой копией на втором носителе и не проверялась reboot/disaster test. Digest подтверждает целостность, не шифрует архив: приватные URL внутри HTML требуют сохранения текущих прав доступа. Старые HTML нельзя публиковать обратно без замены legacy authority на owned authority.

### Frozen state и уточнённый исполнительный пакет

`FACT` — до backup и в отдельной последующей strict-pinned SSH-сессии page guard `61a36ceb21976cb1201b14681e9f7c79182302e8067bca2124802085d10bc251` и protected guard `7f517d021fc6189b1b4b47e52c38a18c8c256c599a2a9c89cf841808231f08c1` совпали с эталонами. Шесть subscriptions и четыре configs не изменились. Текущий адрес присутствует на интерфейсе, старый отсутствует. Все четыре units active/running, NRestarts=0; PID совпали с ночным и утренним checkpoint. Это read-only state proof, не новый data-path PASS.

`FACT` — три RAM candidates снова прошли проверку единственного metadata tag: меняется только authority; scheme/port/path/token/query/fragment и все bytes вне tag прежние; обратная substitution восстанавливает оригинал. Candidate SHA-256 и приватная allowlist сохранены в private manifest. Production candidates/staging на VPS не записывались.

`DECISION` — проект G1/G2 и forward-only recovery выше сохраняется со следующими точными уточнениями:

1. `TODO` — сначала закрыть DNS API blocker, добавить полный снимок ровно одной записи в существующий private backup, повторно проверить его и оба frozen guards. Не создавать record_id по догадке и не переходить к write через UI ради обхода gate.
2. `TODO` — G1: после отдельного разрешения один PATCH проверенного record_id. Исходные `type=A`, exact name, `ttl=1` (Auto) и `proxied=false` сохраняются; единственная целевая semantic delta — content на CURRENT_ADDRESS. Не записывать `ttl=300`: это изменило бы настройку Auto. Перед PATCH свежий GET и сравнение с полным snapshot; при drift STOP. После PATCH GET с проверкой всех protected business fields. Timeout — один GET и STOP при неизвестном outcome, без blind retry.
3. `TODO` — propagation: по наблюдаемому effective TTL=300 выбрать конечное окно максимум 10 минут, проверки с интервалами до 60 секунд, два resolver обязаны выбрать CURRENT_ADDRESS. Это bounded verification window, не гарантия всех локальных caches. G2 не начинать, если DNS gate не прошёл.
4. `TODO` — G2: читать private manifest и durable backup, повторно проверять оба guards; эксклюзивный same-FS private stage вне public root. Ровно три candidate, последовательный atomic file replace с no-follow/dirfd, fresh source hash/mode/owner/nlink checks и fsync file/parent. После каждого файла — exact candidate hash receipt/readback; перед следующим — остальные source guards плюс ранее опубликованные receipt hashes. При любой ошибке STOP без чужих overwrite/delete. Это три атомарные file операции, не общая транзакция.
5. `TODO` — финальный G2 PASS: 6/6 owned metadata, прежний protected digest, полное local TLS/body/hash сравнение всех 12 файлов. Затем отдельный внешний HTTPS и настоящий Happ refresh/клиентская приёмка; прежние результаты I/II не обновлять датой G0. III UDP/QUIC остаётся NOT_TESTED.
6. `DECISION` — recovery только вперёд: не возвращать OLD_ADDRESS и не публиковать активные legacy links. После подтверждённого G1 safe A сохраняется даже при внешнем HTTPS failure. Повреждённый собственный опубликованный HTML ремонтируется только при receipt hash match, из проверенного backup с повторным применением owned authority. Без успешного безопасного ремонта — STOP; maintenance fallback не включать автоматически, он требует явного включения в будущее разрешение.

`TODO` — риск G1: ошибочная identity записи/конкурентная правка/cache propagation; риск G2: ошибка точечной публикации и частично завершённый набор из трёх файлов. Сохранённые оригиналы и проверенные candidates закрывают HTML recovery, но не заменяют полный DNS snapshot. Нельзя считать этот проект уже проверенным production executable, пока обязательный API read заблокирован.

`DECISION` — итог: `HTML_BACKUP_BLOCKER=CLOSED`, `DNS_LOGIN_BLOCKER=CLOSED`, `DNS_RECORD_ID_AND_FULL_SNAPSHOT_BLOCKER=OPEN`. `AMSTERDAM_G0=PARTIAL_STOP`; G0 PASS и готовность одного production-решения не объявляются. Центральному архитектору нужен именно безопасный read-only API/record-details доступ; технические команды и журналы через владельца не запрашивались. Другие сетевые тесты/изменения вместо недостающего DNS identity не выполняются.

## UI-G1 — альтернативная процедура для утверждения, 16 октября, 13:04–13:06 UTC

`DECISION` — новое прямое поручение разрешает подготовить штатный UI-вариант без обязательного API record_id. Для этого варианта прежнее требование полного API snapshot заменяется проверяемым snapshot всех отображаемых полей, однозначным выбором записи и явным принятием ограничений UI. Это проект альтернативы, не разрешение исполнения и не обход блокировки API. API-вариант выше остаётся заблокированным; его prerequisites не переносятся автоматически на UI-G1.

### Проверка осуществимости без записи

`FACT` — использована прежняя авторизованная Chrome-вкладка Records в нужном account/zone. Exact full-host search показал одну карточку, `Showing 1-1 of 1`; она раскрывается через собственный `Expand … record`. В карточке ровно одна form. Bulk selection не отмечен. Поле `IPv4 address` enabled и не read-only. Save disabled при исходных данных. Это подтверждает доступность отдельной формы, но не доказывает успешность будущего write, серверные write permissions или поведение сохранения.

| Отображаемое поле / контроль | Факт до и после reload | Требование будущего postcheck |
|---|---|---|
| Account и zone | Прежние account URL и заголовок нужной зоны | Тот же account/zone, не соседний ресурс |
| Полное имя | Short name + zone suffix совпадают с DELIVERY_HOST; одна карточка | DELIVERY_HOST, одна карточка, тот же exact search |
| Type | A | A |
| IPv4 address | OLD_ADDRESS | Только CURRENT_ADDRESS |
| Proxy status | DNS only, switch `aria-checked=false` | DNS only / false |
| TTL | Auto; связанное control value `1` | Auto / 1, не ручные 300 секунд |
| Record Attributes | Раскрыты; показан только Comment, он пуст | Comment пуст; любые дополнительно появившиеся поля сверить до write |
| Другие controls | Save, Cancel, Delete; отдельные combobox Type/TTL | Не использовать Delete, bulk, Add record, Import/Export, proxy switch |

`FACT` — выполнены раскрытие, DOM/read-only чтение полей, Cancel, один reload Records, повторное раскрытие/сравнение и Cancel. Значения name/content/type/proxy/TTL/comment прежние, Save оставался disabled. Никакое поле DNS-записи не заполнялось; ни Save, ни Enter в record form не нажимались. Auth/API/VPS/HTML/backup операции не выполнялись.

`FACT` — [официальная процедура Cloudflare](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/) предусматривает выбор конкретной записи, Edit, изменение полей и Save; для изменения origin IP требуется её content. Текущая форма открывается через Expand, без отдельного шага Edit. Штатная форма сама связывает Save со своей записью; это достаточный наблюдаемый UI scope для предложения процедуры, а не независимая проверка внутреннего record_id или request payload.

### Предлагаемый исполнительный пакет — только после нового разрешения

`TODO` — Target: ровно существующая A-запись DELIVERY_HOST в зафиксированной зоне. Reason: OLD_ADDRESS больше не принадлежит владельцу. Impact: после DNS propagation новые запросы к owned hostname направятся на CURRENT_ADDRESS. DNS-only, Auto, имя/type/comment не меняются. VPS, сертификаты, HTML и subscriptions не входят в UI-G1. Исправление трёх metadata остаётся отдельным G2.

1. `TODO` — **Preflight:** проверить отдельное разрешение именно на UI-G1, точный CURRENT_ADDRESS из утверждённого приватного packet и принятие forward-only recovery. Ранее проверенный private HTML backup остаётся прежним prerequisite G2; в этой миссии он не перечитывался. Для UI-G1 достаточно сохранённого private UI before-snapshot; нельзя называть его полным API backup. Перед выполнением сохранить свежие отображаемые before-values и временные отметки в существующем private operator space без cookies/tokens/общего zone export. Не менять уже созданный HTML archive.
2. `TODO` — **Fresh selection:** открыть нужный account/zone → Records; без открытой изменённой формы reload → exact full-host search. Дождаться окончания loading. Требовать ровно один результат на единственной странице, exact имя/type/content, отсутствующие конфликтующие A/AAAA/CNAME в результатах этого имени, никакого bulk selection. Все locators должны разрешаться ровно в один элемент. Сверить не по позиции строки, а по account + zone + FQDN + type + OLD_ADDRESS + DNS only + Auto.
3. `TODO` — **Fresh form:** раскрыть только эту карточку, Record Attributes; прочитать все видимые поля и сравнить с таблицей. Поля, не показанные в этой версии UI, не считать отсутствующими в backend. Если появились новые поля/metadata — сначала включить их в before-snapshot и пересмотреть packet, без write. Нужен короткий согласованный период без параллельных изменений этой записи другими операторами. UI не предоставляет наблюдаемого CAS/lock: остаётся race между чтением и Save.
4. `TODO` — **Единственное изменение формы:** внутри exact target article выбрать textbox `IPv4 address` и выполнить только `fill(CURRENT_ADDRESS)`. Не заполнять name/comment, не выбирать Type/TTL, не переключать proxy, не нажимать Enter. Повторно прочитать форму: единственная delta относительно before должна быть IPv4 address. Ровно одна target form и одна её Save; Save должен стать enabled. Любая дополнительная delta/validation error/двусмысленность — Cancel при известном несохранённом состоянии и STOP.
5. `TODO` — **Публикация:** только после отдельного owner gate и успешного pre-save сравнения нажать ровно один раз Save, scoped к этой карточке/form. Записать время и наблюдаемый outcome. Не использовать глобальный первый Save, клавиатурный submit, bulk, скрытые API или повторную отправку. Подготовительный этап этого не проверял и не выполнял.
6. `TODO` — **Control-plane postcheck:** после завершения сохранения заново найти exact host, проверить одну A-карточку, раскрыть и сверить все поля: CURRENT_ADDRESS и прежние name/type/DNS only/Auto/comment. Одного toast/исчезновения формы недостаточно. Закрыть неизменённую форму Cancel, сделать один reload Records и повторить свежий readback. Успешная форма/уведомление без подтверждённого persisted readback не дают PASS. Сохранить private after-snapshot и proof screenshot без auth data; в публичный PR — только санитизированный receipt, не сырой снимок панели.
7. `TODO` — **DNS postcheck:** Google и Cloudflare DoH для exact hostname, A и AAAA; ожидать единственный CURRENT_ADDRESS и отсутствие неожиданного AAAA. Auto имеет effective TTL 300 секунд по ранее проверенному reference. Наблюдение ограничить 10 минутами от Save, до 60 секунд между попытками, без cache flush/сетевых переключений. При deadline — STOP propagation с доказательствами; не возвращать старый IP и не повторять Save. Это не обещание обновления caches всех устройств.
8. `TODO` — **Граница результата:** UI-G1 PASS требует persisted UI readback всех видимых полей и двух resolver checks. Без API нельзя доказать неизменность скрытых tags/settings/internal IDs или увидеть точный payload. Эту границу owner должен принять до исполнения. Сохранённый UI snapshot позволяет сравнить видимые поля, а не полностью восстановить backend record. External HTTPS/delivery, сохранённые Happ source URLs, metadata G2 и III acceptance остаются самостоятельными checks; DNS PASS не является VPN PASS и сам по себе не открывает G2 без разрешения.

### PASS / STOP / безопасное восстановление

| Событие | Действие / verdict предлагаемого run |
|---|---|
| UI target/forms/поля совпали, IPv4 редактируемый | `UI_PREFLIGHT=PASS`; до разрешения Save запрещён |
| После Save persisted UI readback совпал, оба resolver выбрали current, неожиданных AAAA нет | `UI_G1=PASS` только в указанной границе наблюдения; не G0/VPN/шесть Happ PASS |
| Не тот account/zone, несколько результатов/страниц, content drift, отсутствует поле, session loss/challenge, changed UI или конкурирующая правка | STOP до Save; не выбирать другую запись и не создавать новую |
| Новый адрес уже стоит до начала write | Не отправлять Save. Read-only проверить текущее состояние и сообщить об изменении baseline; не приписывать результат этому run |
| Проверка формы перед Save не прошла | Cancel только при известном несохранённом состоянии; STOP без production write |
| Save timeout/error или outcome неизвестен | Не нажимать Save повторно. Один различающий read-only reload/exact-record readback. CURRENT_ADDRESS со всеми ожидаемыми полями — фиксировать известный результат и STOP для оценки, не продолжать автоматически. OLD_ADDRESS — фиксировать отсутствие подтверждённой правки и STOP. Неизвестный/иной результат — STOP без новых writes |
| CURRENT_ADDRESS persisted, но resolver/HTTPS не прошёл | Оставить безопасный current A, STOP соответствующего path; не возвращать OLD_ADDRESS и не удалять запись |
| После Save изменились другие поля / запись исчезла / обнаружен conflict | STOP, сохранить before/after evidence; никаких автоматических overwrite, delete/recreate или попыток «вернуть всё» |
| Для продолжения требуется API/token/более широкие права или изменение VPS | STOP; это отдельное решение, не часть UI-G1 |

`DECISION` — inverse DNS rollback на OLD_ADDRESS запрещён, поскольку destination чужой. Recovery этого минимального пакета — сохранить подтверждённый safe current A и прекратить изменения при сбое. Если безопасный current A не подтверждён, нельзя угадывать исправление; нужны evidence и новое решение. Backup старого content не является безопасным DNS rollback. Maintenance record, удаление DNS, ручной возврат proxy/TTL и любые вторые корректирующие writes автоматически не разрешаются.

`TODO` — остаточный риск UI-варианта: нет наблюдаемого CAS, полного API snapshot, полного postcheck скрытых полей или доказательства server-side write permission до реального сохранения. Если требуется гарантия неизменности всех backend business fields, UI недостаточен; минимальное решение тогда — ранее описанный safe authenticated API read. Для ограниченной правки через штатную форму record_id не обязателен при явном принятии перечисленных UI-границ.

`DECISION` — `UI_TARGET_SELECTION=PASS`, `UI_FORM_INSPECTION=PASS`, `UI_G1_PROCEDURE=READY_FOR_REVIEW`, `UI_G1_WRITE=NOT_RUN`, `G0_PASS=NOT_DECLARED`, `EXECUTION_AUTHORIZED=false`. Владелец может одним отдельным решением разрешить ровно описанный UI-G1 с его ограничениями и forward-only recovery; нынешнее поручение не разрешает Save. G2 не добавляется в это разрешение автоматически. Полная диагностика, backup и существующие клиентские тесты не повторялись.

## Безопасность, валидация и STOP

- `FACT` — перед публикацией отчёта ранее прошли существующие 26 generator tests. Это не live VPN acceptance.
- `FACT` — диагностические commands не записывали VPS configs/subscriptions/HTML/DNS/trust и не перезапускали units; после проб все четыре units сохранили PID/NRestarts. Разрешённые постоянные writes текущего этапа — только private operator backup и документация рабочей ветки. Ночные Windows client configs были только в памяти, собственные процессы завершены, рабочие Xray PID сохранены. Новое ПО не устанавливалось.
- `FACT` — Primary DeepWork и PP-LAB-01 не использовались как targets/control hosts; payment/deployment/merge отсутствуют.
- `TODO` — результаты staged/full-diff Gitleaks, manual sanitization, GitHub readback и CI для этой редакции фиксируются в существующем Draft PR. Нельзя считать прежний CI проверкой нового commit.
- `TODO` — не проверены Android/прямые RF-сети, реальные source URLs шести телефонов, III UDP data path и formal acceptance. Причина loss до delivery listener и недоступность полного API snapshot остаются ограничениями; UI-G1 явно ограничен отображаемыми полями и публичным DNS.
- `DECISION` — любые production изменения STOP до отдельного разрешения. Ближайший полезный шаг — review и отдельное утверждение UI-G1 владельцем с принятием его residual risks и forward-only recovery; если нужен полный backend-fields proof, сначала решить API blocker. Ни один вариант не означает разрешение G2 или доказательство внешней доставки.
