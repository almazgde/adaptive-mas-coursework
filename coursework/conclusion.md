# Заключение

В ходе работы был реализован и расширен исследовательский прототип адаптивной оркестрации многоагентных LLM-систем на основе DAG. Итоговая версия проекта включает модель графа задач, структурные и weighted graph metrics, статические топологии исполнения, rule-based, cost-aware и learned adaptive selector, execution layer с tracing, benchmark framework, Gantt visualization, quality evaluation, failure simulation and recovery logic, CLI/config layer и набор unit tests.

Главный результат работы состоит в том, что прототип теперь оценивает orchestration strategies не только по latency и synthetic execution cost, но и по более широкому набору критериев:

1. weighted critical path и распределение стоимости узлов;
2. coordination overhead и worker utilization;
3. heuristic quality metrics;
4. robustness metrics при synthetic failures;
5. воспроизводимость экспериментов через fixed seed и сохранение конфигурации запуска.

Первоначальная структурная эвристика adaptive selector была сохранена как `rule_based_adaptive`, но дополнена режимом `cost_aware_adaptive`. Новый режим оценивает все поддерживаемые топологии до выбора и использует простую интерпретируемую функцию:

```text
score = expected_latency + coordination_overhead + critical_path_penalty
```

Это не делает adaptive strategy универсально лучшей, но делает выбор более осмысленным в тех случаях, где структура DAG сама по себе недостаточна для прогноза latency.

Дополнительно реализован `learned_adaptive` selector. Он использует nearest-neighbor baseline по признакам DAG и обучается на synthetic benchmark data. Objective score для обучения задан явно: `estimated_latency_with_overhead + 0.05 * execution_cost`. Этот компонент не является полноценной ML-системой, но показывает следующий исследовательский шаг: переход от ручных эвристик к выбору topology на основе накопленных экспериментальных данных.

Добавление weighted metrics уточнило модель DAG. Теперь критический путь может измеряться не только числом узлов или рёбер, но и суммарной стоимостью задач. Это важно для multi-agent systems, где разные агенты и подзадачи могут иметь различную стоимость исполнения.

Quality evaluation и robustness evaluation расширили экспериментальную методику. Качество результата оценивается эвристически по trace: полнота выполнения, наличие synthesis/aggregate шага, согласованность результатов и соблюдение зависимостей. Robustness layer позволяет моделировать exception, timeout и empty result, а также проверять retry, fallback и skipped descendants. Благодаря этому проект ближе к реальным условиям многоагентных систем, где важны не только скорость, но и устойчивость.

Также был добавлен единый CLI `run.py` и JSON config support. Это упрощает воспроизведение экспериментов и делает проект удобнее для проверки: параметры запуска фиксируются в `experiment_config_used.json`, а benchmark outputs сохраняются в выбранный output directory.

## Ограничения

Работа имеет несколько ограничений.

Во-первых, используются mock agents, а не реальные LLM backend. Поэтому результаты не являются измерением фактической задержки или стоимости API-вызовов.

Во-вторых, quality evaluation является heuristic model. Она проверяет структуру trace и наличие результатов, но не оценивает семантическую правильность сгенерированного текста.

В-третьих, failure model является synthetic. Вероятности exception, timeout и empty result задаются конфигурацией и не калиброваны на реальных production traces.

В-четвёртых, cost-aware selector использует простую аналитическую scoring formula. Она интерпретируема и не гарантирует оптимальность для всех типов графов.

В-пятых, learned selector является nearest-neighbor baseline. Его качество зависит от synthetic training set, выбранных features и objective score. Он не заменяет learned policy, обученную на реальных traces.

В-шестых, synthetic benchmark graphs являются упрощением реальных task graphs. Реальные задачи могут иметь динамически возникающие подзадачи, изменяемую структуру зависимостей и более сложную семантику результатов.

## Future work

Перспективы дальнейшего развития:

1. подключить real LLM backend и измерять реальные latency/cost traces;
2. откалибровать overhead и failure model на реальных execution logs;
3. развить текущий learned selector от nearest-neighbor baseline к более сильной learned policy;
4. откалибровать objective score learned selector на реальных traces;
5. добавить online adaptation во время исполнения DAG;
6. расширить quality evaluation с использованием human/LLM judge при наличии реальных ответов;
7. добавить больше типов synthetic и real-world task graphs.

Таким образом, проект демонстрирует, что adaptive orchestration целесообразно рассматривать как многокритериальную задачу. Минимальная latency важна, но полноценная оценка многоагентной системы также требует анализа стоимости, качества, отказоустойчивости и воспроизводимости экспериментов.
