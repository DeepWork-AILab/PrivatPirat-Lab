# PP-LAB Builder — article seeds from predeploy day

**Date:** 2026-08-30  
**Status:** `EDITORIAL SEEDS / NOT FOR PUBLICATION YET`

## Seed A — Field Note

### Working title

**Когда безопасная автоматизация начинает мешать: чему нас научил запуск, который ещё не дошёл до сервера**

### Thesis

Безопасный automation workflow может формально предотвращать вред и одновременно быть плохим продуктом, если требует слишком много operator attention. Настоящая зрелость начинается, когда safety preconditions становятся встроенными, проверяемыми и почти незаметными на нормальном пути.

### Useful episodes

- root assumption опровергнут простым UID probe;
- passwordless sudo capability обнаружена до deployment;
- broad secret scanner остановил safe negative tests;
- hard-coded `/tmp` сломал Termux tests;
- generated `__pycache__` вызвал ложный dirty-tree STOP;
- VPS остался нетронутым несмотря на несколько tooling failures;
- человек остановил drift и вернул процесс к исходной цели: one Builder invocation.

### Reader takeaway

Система должна измерять два риска одновременно:

1. blast radius неправильного действия;
2. cognitive/operator burden правильного действия.

## Seed B — Technical article

### Working title

**Root без root-login: как проектировать безопасный privileged transport для VPS Builder**

### Scope

Не инструкция по конкретному серверу, а архитектурный разбор:

- почему username не является capability;
- direct UID 0 vs proven `sudo -n`;
- почему password piping плохая граница;
- privileged stdin shell transport;
- secret-safe file streaming;
- ControlMaster и единичная interactive SSH authentication;
- fail-closed privilege probe;
- tests для root mode, sudo mode и rejection mode.

### Evidence boundary

Не включать working addresses, fingerprints, logins, SNI, keys, UUID, ports или client URIs.

## Seed C — Engineering-method article

### Working title

**Почему grep не является security proof: тестируем safety checks как обычный production code**

### Thesis

Security scanner, guardrail и wrapper — такой же код, как основной продукт. У него есть false positives, portability bugs и hidden assumptions. Поэтому guardrails должны иметь собственные unit/structural tests.

### Examples from lab

- token name inside negative test fixture;
- structural invariants for protected route functions;
- generated artifacts vs tracked source integrity;
- distinguishing read-only test before code change.

## Seed D — Smartphone-first automation

### Working title

**Termux как production environment, а не запасной терминал**

### Angle

Если пользователь реально разворачивает инфраструктуру со смартфона, mobile shell нельзя считать просто Linux-like environment. Path assumptions, clipboard UX, process persistence, keyboard signals, VPN routing и app switching становятся частью production architecture.

### Strong sentence candidate

> Smartphone-first — это не «скрипт запускается на Android». Это значит, что весь verified path от authorization до recovery не требует возвращаться к ноутбуку или превращать человека в транспортный слой.

## Editorial gate

Ни один seed не объявлять финальной статьёй до clean-room Builder result. После реального run обновить:

- что оказалось полностью автоматическим;
- где человек всё ещё был необходим;
- сколько network switches и private inputs осталось;
- сколько unexpected stops произошло;
- смог ли Builder завершить I/II/III без ручной server repair.
