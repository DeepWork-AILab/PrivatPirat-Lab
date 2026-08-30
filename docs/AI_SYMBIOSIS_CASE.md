# PrivatPirat Lab как кандидат AI Symbiosis Field Notes

## Вердикт

**Подходит как полноценный кандидат на серию Field Notes, но отдельные тексты всё ещё должны проходить редакционный gate перед публикацией.**

`FACT` — исходный трёхмаршрутный эксперимент завершён: `PP-LAB-I`, `PP-LAB-II` и `PP-LAB-III` формально приняты по действующему protocol baseline. G2/G3/G4 = PASS.

`FACT` — следующим реальным workstream стал `PrivatPirat Reproducible Node Builder v0.1`: попытка превратить доказанный ручной/staged baseline в воспроизводимый инструмент, который работает без AI на стороне конечного пользователя.

Самостоятельный GitHub-репозиторий остаётся техническим source of truth. Публикация конкретной статьи требует отдельного решения и не следует автоматически из PASS технического gate.

## Почему соответствует

- Решается реальная практическая задача с измеримым результатом.
- AI участвует в изучении канона, сравнении источников, проектировании gates, тестов и rollback boundaries.
- Человек сохраняет оркестрацию, разрешает изменения и принимает конечный verdict.
- Процесс специально повышает вероятность обнаружения ошибки: `Expected/Actual`, independent data-path tests, restart, isolation, regressions и distinguishing read-only checks.
- Эксперимент уже показал границу между полезной автоматизацией, ложной уверенностью и лишней сложностью.
- Builder workstream добавил новый слой: цена operator attention и качество UX теперь рассматриваются как часть инженерного результата, а не как косметика.

## Что уже появилось в реальном опыте

- `FACT` — I/II/III прошли формальную приёмку с Wi‑Fi/mobile data path, reconnect, restart/isolation и обязательными regressions.
- `FACT` — AI ранее ошибочно перенёс JSON одного клиентского диалекта в другой формат; ошибка была поймана до сетевого соединения.
- `FACT` — AI ранее преждевременно называл промежуточный connectivity result завершённым PASS; протокол заставил отделить service state от доказанного data path.
- `FACT` — один restart-result оказался ложным отрицанием из-за смешения control path и route-under-test; это привело к правилу их разделения.
- `FACT` — Builder implementation выявил ещё несколько process/tooling errors до первого clean-room server write: неверное root assumption, ложноположительный secret scan, непереносимый `/tmp`, misclassified `__pycache__` и operator friction вокруг wrapper-команд.
- `FACT` — все эти predeploy failures остановились безопасно и не привели к изменению clean-room target.
- `DECISION` — ошибки процесса фиксируются не как набор случайных команд, а как правильные решения и переносимые методы.

## Текущий Builder checkpoint

`FACT` — текущий Builder поддерживает reviewed `--apply` entrypoint и capability-based privilege transport: direct root или независимо доказанный passwordless `sudo -n`.

`FACT` — last local suite: 46 tests PASS, render check PASS, structural checks PASS.

`FACT` — clean-room acceptance ещё не завершён; на текущем predeploy checkpoint серверные route writes не начинались.

Подробности:

- [`PP-LAB-BUILDER-PREDEPLOY-CHECKPOINT-2026-08-30.md`](evidence/PP-LAB-BUILDER-PREDEPLOY-CHECKPOINT-2026-08-30.md)
- [`PP-LAB-BUILDER-PREDEPLOY-LESSONS-2026-08-30.md`](field-notes/PP-LAB-BUILDER-PREDEPLOY-LESSONS-2026-08-30.md)
- [`PP-LAB-BUILDER-ARTICLE-SEEDS-2026-08-30.md`](field-notes/PP-LAB-BUILDER-ARTICLE-SEEDS-2026-08-30.md)

## Классификация

- `FACT` — концепция Field Notes требует реального эксперимента, проверяемости, отделения фактов от гипотез и ответственности человека.
- `DECISION` — PrivatPirat Lab ведётся как отдельный публичный технический проект.
- `DECISION` — technical manual и Field Note остаются разными типами материалов.
- `FACT` — трёхмаршрутный baseline уже даёт завершённый технический сюжет.
- `HYPOTHESIS` — clean-room Builder run может дать более сильный сюжет о том, как письменное governance превращается в executable governance.
- `TODO` — завершить первый clean-room Builder acceptance и измерить реальную цену operator attention на нормальном пути.

## Что фиксировать во время работы

Для каждого существенного шага сохранять санитизированную полевую запись:

```text
Ситуация и реальная цель:
Что предложил AI:
Что решил человек и почему:
Как предложение проверяли:
Где обнаружилось противоречие или ошибка:
Что изменилось в методе работы:
Цена по времени, вниманию и сложности:
Фактический технический результат:
Переносимый вывод для читателя:
```

Особенно ценны случаи, где:

- простой read-only test оказался полезнее сложной автоматизации;
- AI уверенно ошибся, а процесс проверки это обнаружил;
- control path оказался связан с route-under-test;
- security guardrail дал false positive и был исправлен без ослабления safety boundary;
- smartphone-first requirement выявил скрытое desktop/Linux assumption;
- человеческое stop decision предотвратило каскад изменений;
- письменное правило оказалось недостаточно сильным и было перенесено в tests/preconditions/UX;
- операторское трение стало измеримым инженерным недостатком.

## Редакционный gate

Не писать статью только потому, что репозиторий создан, сервис запустился или automation test прошёл.

Материал достоин публикации, если он одновременно:

1. содержит проверяемый практический результат;
2. показывает ошибку, ограничение или новый способ работы;
3. отделяет факты, решения и гипотезы;
4. даёт читателю метод, который можно проверить в собственной ситуации;
5. не раскрывает operational secrets;
6. не обещает универсальную работоспособность на основании единичного теста;
7. честно показывает цену внимания и ручного участия.

## Возможный публичный выход

После доказательного завершения Builder workstream возможны как минимум четыре разных материала:

- русскоязычный technical manual о staged reproducible node build;
- Field Note о человеческой оркестрации AI и проверке ошибок;
- технический разбор capability-based privileged transport;
- отдельный материал о smartphone-first automation и operator burden.

Их не следует смешивать. Manual отвечает «как воспроизвести», Field Note — «что этот опыт показал о совместной работе человека и AI», а implementation article — «какие инженерные решения сделали процесс проверяемым».

Текущий ранний редакционный прототип первого маршрута: [`PP-LAB-I-FIRST-WORKING-PATH.md`](field-notes/PP-LAB-I-FIRST-WORKING-PATH.md).
