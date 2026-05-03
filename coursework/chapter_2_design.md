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
| `experiments/benchmarks` | synthetic graph generation and benchmark runner |
| `results` | CSV, traces и изображения графиков |

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

Эта эвристика намеренно проста. Она делает выбор интерпретируемым и пригодным для анализа, но не гарантирует оптимальность. Экспериментальные результаты подтверждают это ограничение: adaptive selector корректно выбрал `parallel` для `wide_sparse` и `sequential` для `deep_dependency`, но не всегда совпал с лучшей статической стратегией по latency для `layered` и `centralized_coordinator`.

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

`BenchmarkRunner` выполняет каждый граф в пяти режимах:

1. static sequential;
2. static parallel;
3. static hierarchical;
4. static hybrid;
5. adaptive.

Для каждого режима выполняется 10 repeated runs. Всего при текущей конфигурации было получено `200` строк в `benchmark_results.csv`: 4 категории графов, 10 повторов и 5 стратегий.

Симулятор benchmark runner рассчитывает latency не через реальные задержки API, а через synthetic node cost и модель накладных расходов. Это даёт воспроизводимость и позволяет сравнивать стратегии в одинаковых условиях.
