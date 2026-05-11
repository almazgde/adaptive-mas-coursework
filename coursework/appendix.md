# Приложение

## Приложение А. Структура реализованного проекта

```text
adaptive_mas/
  agents/
    mock_agents.py
  dag/
    node.py
    edge.py
    dag.py
  execution/
    executor.py
  evaluation/
    quality.py
    robustness.py
  metrics/
    graph_metrics.py
  topology/
    selector.py

experiments/
  benchmarks/
    synthetic_graphs.py
    runner.py

configs/
  experiment_default.json

tests/
  test_*.py

run.py
visualize_execution_timeline.py

results/
  benchmark_results.csv
  benchmark_summary.csv
  experiment_config_used.json
  latency_comparison.png
  topology_efficiency.png
  adaptive_vs_static.png
  critical_path_impact.png
  timeline_<trace>_<topology>.png
```

## Приложение Б. Команды запуска экспериментов

```powershell
.\.venv\Scripts\python.exe run_benchmarks.py
.\.venv\Scripts\python.exe visualize_results.py
.\.venv\Scripts\python.exe run.py experiment --config configs/experiment_default.json
.\.venv\Scripts\python.exe run.py visualize --trace results/execution_trace.json
```

## Приложение В. Поля `benchmark_results.csv`

| Поле | Содержание |
|---|---|
| `run_id` | номер repeated run |
| `strategy_group` | static или adaptive |
| `requested_topology` | запрошенная стратегия |
| `topology` | фактически выбранная топология |
| `graph_type` | категория synthetic graph |
| `node_count` | число узлов |
| `edge_count` | число рёбер |
| `graph_depth` | глубина DAG |
| `critical_path_length` | длина критического пути |
| `execution_latency` | итоговая задержка исполнения |
| `critical_path_latency` | latency критического пути |
| `execution_cost` | synthetic execution cost |
| `parallel_efficiency` | эффективность относительно critical path |
| `coordination_overhead` | накладные расходы координации |
| `executor_utilization` | использование executor capacity |

## Приложение Г. Сводная таблица adaptive vs best static

| Graph type | Adaptive selected | Adaptive latency | Best static | Best static latency |
|---|---|---:|---|---:|
| wide_sparse | parallel | 0.56404 | parallel | 0.56404 |
| deep_dependency | sequential | 1.84883 | sequential | 1.84883 |
| layered | hybrid | 0.67070 | parallel | 0.641033 |
| centralized_coordinator | hierarchical | 0.66837 | parallel | 0.541673 |

## Приложение Д. Перечень графиков

| Файл | Назначение |
|---|---|
| `results/latency_comparison.png` | сравнение latency по topology и graph type |
| `results/topology_efficiency.png` | сравнение parallel efficiency |
| `results/adaptive_vs_static.png` | сравнение adaptive и static strategies |
| `results/critical_path_impact.png` | влияние critical path latency на total latency |
| `results/graph_wide_sparse.png` | структура wide sparse graph |
| `results/graph_deep_dependency.png` | структура deep dependency graph |
| `results/graph_layered.png` | структура layered graph |
| `results/graph_centralized_coordinator.png` | структура centralized coordinator graph |

## Приложение Е. Актуальные команды CLI

```powershell
python run.py demo --scenario wide_sparse
python run.py train-selector --runs 100 --output results/learned_selector_model.json
python run.py benchmark --runs 5 --graph layered --selector cost_aware
python run.py benchmark --selector learned_adaptive --model results/learned_selector_model.json
python run.py visualize --trace results/execution_trace.json
python run.py experiment --config configs/experiment_default.json --runs 5 --random-seed 7
```

## Приложение Ж. Дополнительные поля результатов

В обновлённой версии `benchmark_results.csv` дополнительно содержит weighted, quality и robustness поля:

| Поле | Содержание |
|---|---|
| `total_node_cost` | суммарная стоимость узлов DAG |
| `avg_node_cost` | средняя стоимость узла |
| `max_node_cost` | максимальная стоимость узла |
| `cost_variance` | разброс стоимости узлов |
| `weighted_critical_path` | weighted critical path |
| `weighted_parallel_width` | максимальная суммарная стоимость уровня |
| `overall_quality_score` | итоговая эвристическая оценка качества |
| `success_rate` | доля успешно выполненных узлов |
| `failed_node_count` | число failed/timeout узлов |
| `skipped_node_count` | число узлов, пропущенных из-за отказов предков |
| `retry_count_total` | суммарное число retry |
| `fallback_count` | число fallback results |
| `recovery_success_rate` | доля успешных восстановлений |
| `wasted_work_estimate` | оценка потраченной впустую работы |
| `selector_mode` | режим selector-а |
| `learned_model_used` | путь к JSON-модели learned selector |
| `objective_score` | objective score выбранной стратегии |

## Приложение З. Тестирование

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest discover -s tests
```

Тесты проверяют DAG operations, graph metrics, weighted metrics, topology selector, executors, execution traces, quality evaluation, failure recovery, benchmark CSV generation, CLI smoke scenarios и reproducibility checks.
