# LilFox Amsterdam — read-only diagnosis и пакет восстановления

`FACT` — утреннее продолжение **AMSTERDAM-G0**: allowlist и dry-run проверены; DNS control plane и durable backup ещё отсутствуют. Текущий write verdict **PARTIAL / STOP**, а не готовность к применению. Актуальный G1/G2 и recovery policy приведены в секции AMSTERDAM-G0 ниже; ночные результаты сохранены как историческое evidence.

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

## AMSTERDAM-G0 — актуальный пакет подготовки, 16 октября утром

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

## Безопасность, валидация и STOP

- `FACT` — перед публикацией отчёта ранее прошли существующие 26 generator tests. Это не live VPN acceptance.
- `FACT` — диагностические commands не записывали VPS configs/subscriptions/DNS/trust и не перезапускали units; после проб все четыре units сохранили PID/NRestarts. На Windows временные client configs были только в памяти, собственные процессы завершены, рабочие Xray PID сохранены. Новое ПО не устанавливалось.
- `FACT` — Primary DeepWork и PP-LAB-01 не использовались как targets/control hosts; payment/deployment/merge отсутствуют.
- `TODO` — результаты staged/full-diff Gitleaks, manual sanitization, GitHub readback и CI для этой редакции фиксируются в существующем Draft PR. Нельзя считать прежний CI проверкой нового commit.
- `TODO` — не проверены Android/прямые RF-сети, реальные source URLs шести телефонов, III UDP data path и formal acceptance. Конкретная причина loss до delivery listener и доступ к DNS control plane остаются ограничениями.
- `DECISION` — после этого read-only этапа любые изменения STOP до отдельного разрешения. Ближайший полезный шаг — завершить приватные DNS snapshot/rollback prerequisites и согласовать G1/G2, сохраняя отдельную проверку внешнего пути.
