# Приложение

## Приложение А. Структура реализованного проекта

```text
adaptive_mas/
  agents/
  dag/
  execution/
  evaluation/
  metrics/
  topology/

experiments/
  benchmarks/

configs/
  experiment_default.json

tests/
  test_*.py

run.py
demo.py
visualize_results.py
visualize_execution_timeline.py

results/
  benchmark_results.csv
  benchmark_summary.csv
  learned_selector_model.json
  experiment_config_used.json
  *.png
  *.json
```

## Приложение Б. Команды запуска

```powershell
python demo.py
python run.py demo
python run.py benchmark --runs 1
python run.py train-selector --runs 100 --output results/learned_selector_model.json
python run.py benchmark --selector learned_adaptive --model results/learned_selector_model.json --runs 10
python run.py benchmark --selector all --model results/learned_selector_model.json --runs 10
python run.py visualize --trace results/execution_trace.json
python run.py experiment --config configs/experiment_default.json --runs 5 --random-seed 7
```

## Приложение В. Основные поля `benchmark_results.csv`

| Поле | Содержание |
|---|---|
| `run_id` | Номер repeated run |
| `graph_type` | Категория synthetic graph |
| `strategy` | Strategy label для анализа |
| `selector_mode` | Static, rule-based, cost-aware или learned adaptive mode |
| `requested_topology` | Запрошенная topology или adaptive mode |
| `selected_topology` | Фактически выбранная topology |
| `learned_model_used` | Путь к JSON-модели learned selector, если применимо |
| `objective_score` | Objective score выбранной стратегии, если применимо |
| `node_count` | Число узлов DAG |
| `edge_count` | Число ребер DAG |
| `graph_depth` | Глубина DAG |
| `parallel_width` | Максимальная ширина DAG |
| `density` | Плотность графа |
| `execution_latency` / `latency` | Итоговая задержка исполнения |
| `execution_cost` / `cost` | Synthetic execution cost |
| `coordination_overhead` | Накладные расходы coordination layer |
| `parallel_efficiency` | Эффективность относительно critical path |
| `overall_quality_score` | Итоговая heuristic quality score |
| `success_rate` | Доля успешно выполненных узлов |

## Приложение Г. Weighted, quality и robustness поля

| Поле | Содержание |
|---|---|
| `total_node_cost` | Суммарная стоимость узлов DAG |
| `avg_node_cost` | Средняя стоимость узла |
| `max_node_cost` | Максимальная стоимость узла |
| `cost_variance` | Разброс стоимости узлов |
| `weighted_critical_path` | Максимальная суммарная стоимость пути |
| `weighted_parallel_width` | Максимальная суммарная стоимость одного уровня |
| `completeness_score` | Полнота выполнения DAG |
| `consistency_score` | Штрафует failed, skipped, empty и fallback results |
| `synthesis_score` | Наличие synthesis/aggregate step |
| `dependency_coverage_score` | Соблюдение dependency constraints |
| `failed_node_count` | Число failed/timeout nodes |
| `skipped_node_count` | Число nodes, пропущенных из-за failed predecessors |
| `retry_count_total` | Суммарное число retry |
| `fallback_count` | Число fallback results |
| `recovery_success_rate` | Доля успешно восстановленных failures |
| `wasted_work_estimate` | Оценка работы, потраченной на неуспешные попытки |

## Приложение Д. Графики и trace files

| Файл | Назначение |
|---|---|
| `results/latency_comparison.png` | Сравнение latency по topology и graph type |
| `results/topology_efficiency.png` | Сравнение parallel efficiency |
| `results/adaptive_vs_static.png` | Сравнение adaptive и static strategies |
| `results/critical_path_impact.png` | Связь critical path latency и total latency |
| `results/timeline_<trace>_<topology>.png` | Gantt chart execution timeline |
| `results/execution_trace.json` | Trace последнего demo/run |
| `results/scenario_*_trace.json` | Trace отдельных demo scenarios |

## Приложение Е. Тестирование

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest discover -s tests
```

Тесты проверяют DAG operations, graph metrics, weighted metrics, topology selector, learned selector, executors, execution traces, quality evaluation, failure recovery, benchmark CSV generation, CLI smoke scenarios и reproducibility checks.

## Приложение Ж. Интерпретация результатов

Актуальные численные результаты следует брать из `results/benchmark_summary.csv`. В приложении не фиксируются вручную старые значения latency, потому что они зависят от текущей реализации, seed, числа runs, node count и выбранной конфигурации. Learned selector следует рассматривать как lightweight baseline, обученный на synthetic benchmark data; он не гарантирует превосходство над static или cost-aware strategies во всех сценариях.
