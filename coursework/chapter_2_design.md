# Глава 2. Архитектура реализованного прототипа

## 2.1. Общая архитектура проекта

Реализованный прототип является исследовательской системой для анализа adaptive orchestration. Его основная цель — не построение production-ready LLM framework, а изолированное изучение того, как структура DAG и выбор топологии влияют на latency, execution cost, coordination overhead и parallel efficiency.

Проект состоит из следующих модулей:

| Модуль | Назначение |
|---|---|
| `adaptive_mas/dag` | модель узлов, рёбер и DAG |
| `adaptive_mas/metrics` | расчёт графовых метрик |
| `adaptive_mas/topology` | выбор и описание топологий |
| `adaptive_mas/execution` | mock execution layer, tracing and logging |
| `adaptive_mas/agents` | mock agents для имитации ролей |
| `adaptive_mas/evaluation` | quality и robustness evaluation |
| `experiments/benchmarks` | synthetic graph generation and benchmark runner |
| `configs` | JSON-конфигурации экспериментов |
| `results` | CSV, traces и изображения графиков |
| `tests` | unit tests и reproducibility checks |

Система не использует реальные LLM API, LangChain, Docker, базы данных, frontend или cloud infrastructure. Это соответствует цели исследования: анализировать orchestration mechanics без внешних факторов, связанных с сетевой задержкой, стоимостью API или нестабильностью ответов моделей.

## 2.2. DAG model

Модель DAG реализована в классах `Node`, `Edge` и `DAG`.

`Node` хранит идентификатор узла, текстовое описание задачи и словарь дополнительных данных. В benchmark framework в поле `data` записывается synthetic execution cost, например значение `cost`, используемое симулятором исполнения.

`Edge` хранит исходный узел, целевой узел и тип зависимости. По умолчанию используется тип `depends_on`.

`DAG` хранит внутренний `networkx.DiGraph`, словарь узлов и список рёбер. Основные операции:

1. добавление узла;
2. добавление ребра;
3. получение successors и predecessors;
4. проверка ацикличности;
5. топологическая сортировка.

Такая реализация позволяет использовать готовые алгоритмы NetworkX и одновременно сохранять собственную предметную модель задач.

## 2.3. Graph metrics

Модуль `GraphMetrics` рассчитывает:

1. `graph_depth`;
2. `critical_path_length`;
3. `graph_density`;
4. `parallel_width`;
5. `node_levels`;
6. `max_degree`.

В ходе реализации Stage 3 была уточнена метрика `parallel_width`: она должна возвращать максимальное количество узлов на одном уровне, а не максимальный номер уровня. Это важно для adaptive selector, потому что ширина графа является прямым индикатором потенциального параллелизма.

`max_degree` используется для обнаружения централизованных структур. Если один узел имеет высокую суммарную входящую и исходящую степень, граф может соответствовать coordinator pattern.

## 2.4. Topology selector

Модуль `TopologySelector` содержит статические стратегии:

1. `_sequential_topology`;
2. `_parallel_topology`;
3. `_hierarchical_topology`;
4. `_hybrid_topology`.

Для adaptive strategy реализованы методы `select_adaptive_topology_type` и `select_adaptive_topology`. Эвристика выбирает:

1. `sequential`, если отношение глубины к числу узлов велико;
2. `hierarchical`, если обнаружен узел с высокой степенью и граф не является слишком глубоким;
3. `parallel`, если ширина велика, а плотность зависимостей низкая;
4. `hybrid` в остальных смешанных случаях.

Эта эвристика намеренно проста. Она делает выбор интерпретируемым и пригодным для анализа, но не гарантирует оптимальность. Финальные эксперименты поэтому сравнивают rule-based режим не только со static baselines, но и с cost-aware и learned adaptive selectors.

## 2.5. Execution layer

Execution layer реализован в модуле `adaptive_mas/execution`. Он содержит:

1. `ExecutionManager`;
2. `BaseExecutor`;
3. `SequentialExecutor`;
4. `ParallelExecutor`;
5. `HierarchicalExecutor`;
6. `HybridExecutor`.

`ExecutionManager` создаёт executor по выбранному `TopologyType`. `BaseExecutor` проверяет ацикличность DAG, запускает исполнение, собирает trace, считает latency и сохраняет результаты.

Реальные agent calls в проекте заменены mock agents. Каждый mock agent асинхронно имитирует работу и возвращает структурированный словарь результата. Это позволяет проверить orchestration layer, но не позволяет делать выводы о качестве текстовых ответов LLM.

## 2.6. Tracing and logging

Execution layer сохраняет:

1. execution trace в `results/execution_trace.json`;
2. metrics log в `logs/execution_metrics.json`;
3. scenario traces для демонстрационных сценариев.

Trace включает тип топологии, порядок исполнения, время начала и завершения, длительность, per-node traces и critical path duration. Эти данные полезны для отладки executor-логики.

Benchmark framework использует отдельный CSV-формат, более подходящий для статистического анализа. Основные результаты сохраняются в `results/benchmark_results.csv`, а агрегированная сводка — в `results/benchmark_summary.csv`.

## 2.7. Benchmark framework

Экспериментальный framework находится в `experiments/benchmarks`.

`SyntheticGraphFactory` создаёт четыре типа synthetic task graphs:

1. `wide_sparse`;
2. `deep_dependency`;
3. `layered`;
4. `centralized_coordinator`.

`BenchmarkRunner` выполняет каждый граф в нескольких режимах:

1. static sequential;
2. static parallel;
3. static hierarchical;
4. static hybrid;
5. `rule_based_adaptive`;
6. `cost_aware_adaptive`.

Число repeated runs задаётся параметром `runs` или JSON config. В текущем CLI/config layer также можно ограничивать graph types, enabled topologies, selector mode и output directory. Поэтому количество строк в `benchmark_results.csv` зависит от фактической конфигурации запуска.

Симулятор benchmark runner рассчитывает latency не через реальные задержки API, а через synthetic node cost и модель накладных расходов. Это даёт воспроизводимость и позволяет сравнивать стратегии в одинаковых условиях.

## 2.8. Weighted metrics layer

В обновлённой архитектуре `GraphMetrics` содержит не только структурные, но и weighted metrics. Основные новые методы:

1. `node_cost(dag, node_id)` — возвращает `node.data["cost"]` или `DEFAULT_NODE_COST`;
2. `total_node_cost(dag)` — суммарная стоимость узлов;
3. `average_node_cost(dag)` — средняя стоимость узла;
4. `max_node_cost(dag)` — максимальная стоимость узла;
5. `cost_variance(dag)` — разброс стоимостей;
6. `weighted_critical_path_length(dag)` — максимальная суммарная стоимость пути;
7. `weighted_parallel_width(dag)` — максимальная суммарная стоимость одного уровня.

Эти метрики используются benchmark runner и cost-aware selector. Благодаря этому выбор topology может учитывать не только форму графа, но и распределение работы между узлами.

## 2.9. Cost-aware adaptive selector

Первоначальный adaptive selector использовал rule-based heuristic: глубину, ширину, плотность и максимальную степень узла. Такая эвристика интерпретируема, но иногда выбирает структурно логичную topology, которая не минимальна по latency.

Поэтому добавлен режим `cost_aware_adaptive`. Он оценивает все поддерживаемые topology:

1. `sequential`;
2. `parallel`;
3. `hierarchical`;
4. `hybrid`.

Для каждой topology рассчитываются expected latency, coordination overhead, critical path impact, worker utilization и parallel efficiency. Итоговый score задаётся простой формулой:

```text
score = expected_latency + coordination_overhead + critical_path_penalty
```

Выбирается topology с минимальным score. Формула намеренно остаётся простой и прозрачной: цель работы состоит не в обучении сложной модели, а в демонстрации того, что cost-aware selection может учитывать weighted DAG и overhead ещё до запуска executor.

## 2.10. Quality evaluation layer

Модуль `adaptive_mas/evaluation` содержит `QualityEvaluator`. Это heuristic evaluator, который не вызывает LLM judge и не оценивает семантику текста. Он анализирует trace и DAG:

1. `completeness_score` — выполнены ли ожидаемые узлы DAG;
2. `consistency_score` — присутствуют ли непустые результаты и нет ли failed/skipped nodes;
3. `synthesis_score` — был ли synthesis или aggregate step;
4. `dependency_coverage_score` — соблюдены ли зависимости;
5. `overall_quality_score` — взвешенное среднее перечисленных сигналов.

Такой слой нужен, чтобы в экспериментах сравнивать не только скорость, но и приближённое качество результата. При этом ограничения модели явно сохраняются: evaluator является детерминированной эвристикой, а не заменой реальной оценки качества LLM-ответа.

## 2.11. Failure simulation и recovery layer

В execution layer добавлен `FailureSimulationConfig`. По умолчанию failure simulation выключена, поэтому прежнее поведение сохраняется. При включении система может симулировать:

1. exception агента;
2. timeout;
3. empty result.

Recovery logic выполняет retry при exception и timeout. Если retry исчерпаны и `fallback_enabled = true`, узел получает fallback result. Если восстановиться не удалось, узел получает статус `failed` или `timeout`, а его потомки помечаются `skipped` и не выполняются. Такая политика выбрана как простая и понятная: потомки не должны использовать отсутствующий результат предка.

Trace каждого узла содержит `status`, `retry_count`, `error_message`, `used_fallback`, `start_time`, `end_time` и `duration`. На основе этих данных `RobustnessEvaluator` рассчитывает success rate, число failed/skipped nodes, количество retry, fallback count, recovery success rate и wasted work estimate.

## 2.12. CLI, configs и reproducibility

Для удобства запуска добавлен единый entry point `run.py` на основе `argparse`. Он поддерживает команды:

1. `demo`;
2. `benchmark`;
3. `visualize`;
4. `experiment`.

Эксперименты могут запускаться из JSON config, например `configs/experiment_default.json`. Config задаёт graph types, node count, runs, worker count, selector mode, enabled topologies, output directory, random seed, параметры failure simulation, quality evaluation и timeline visualization. CLI позволяет переопределять отдельные параметры config через command line arguments.

Benchmark/experiment сохраняет копию использованной конфигурации в `experiment_config_used.json`, что повышает воспроизводимость и упрощает проверку результатов.

## 2.13. Learned adaptive selector

Дополнительным расширением selector layer является `learned_adaptive`. Он реализован как lightweight baseline без внешних ML-зависимостей. Вместо обучения сложной модели используется nearest-neighbor classifier по вектору признаков графа.

Feature vector включает:

1. `node_count`;
2. `edge_count`;
3. `graph_depth`;
4. `density`;
5. `parallel_width`;
6. `max_degree`;
7. `total_node_cost`;
8. `average_node_cost`;
9. `max_node_cost`;
10. `weighted_critical_path`;
11. `weighted_parallel_width`.

Training data генерируется на synthetic DAG benchmark graphs. Для каждого графа оцениваются все static topology strategies, после чего в качестве label сохраняется topology с минимальным objective score:

```text
objective_score = estimated_latency_with_overhead + 0.05 * execution_cost
```

Модель сохраняется в JSON-файл, например `results/learned_selector_model.json`. Файл содержит feature names, training samples, objective score description и selector version. Такой подход не является полноценной ML-моделью, но служит научным baseline для сравнения rule-based, cost-aware и learned adaptive selection.
