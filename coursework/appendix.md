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
  metrics/
    graph_metrics.py
  topology/
    selector.py

experiments/
  benchmarks/
    synthetic_graphs.py
    runner.py

results/
  benchmark_results.csv
  benchmark_summary.csv
  latency_comparison.png
  topology_efficiency.png
  adaptive_vs_static.png
  critical_path_impact.png
```

## Приложение Б. Команды запуска экспериментов

```powershell
.\.venv\Scripts\python.exe run_benchmarks.py
.\.venv\Scripts\python.exe visualize_results.py
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
