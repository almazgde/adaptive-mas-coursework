# Глава 3. Экспериментальное исследование

## 3.1. Цель экспериментов

Цель экспериментов состоит в сравнении topology strategies для исполнения DAG-задач в многоагентной системе. В отличие от исходной версии проекта, финальная методика учитывает не только latency и cost, но также weighted graph metrics, quality metrics, robustness metrics и reproducibility checks.

Benchmark runner сохраняет детальные результаты в `results/benchmark_results.csv`, а агрегированную статистику - в `results/benchmark_summary.csv`. Численные значения в этой главе намеренно не дублируются вручную: актуальная таблица формируется кодом при финальном запуске benchmark, что снижает риск расхождения документации и результатов.

## 3.2. Synthetic graph categories

В экспериментах используются четыре категории synthetic DAG:

1. `wide_sparse` - широкий разреженный граф с большим потенциалом параллелизма;
2. `deep_dependency` - глубокая цепочка зависимостей, где critical path близок ко всему графу;
3. `layered` - граф со слоями, допускающий параллельное исполнение внутри слоя;
4. `centralized_coordinator` - граф с выраженным coordinator/aggregate pattern.

Эти категории не моделируют все возможные реальные workflows, но позволяют проверить, как selector реагирует на различную глубину, ширину, плотность и распределение стоимости узлов.

## 3.3. Сравниваемые режимы

Финальный benchmark сравнивает следующие стратегии:

1. static `sequential`;
2. static `parallel`;
3. static `hierarchical`;
4. static `hybrid`;
5. `rule_based_adaptive` - выбор topology по структурным эвристикам DAG;
6. `cost_aware_adaptive` - выбор topology по простой cost model;
7. `learned_adaptive` - lightweight learned baseline на основе synthetic benchmark data.

Rule-based selector использует depth, width, density и max degree. Cost-aware selector дополнительно оценивает expected latency, coordination overhead, critical path penalty и parallel efficiency. Learned selector использует стабильный feature vector из структурных и weighted metrics и выбирает topology через nearest-neighbor model, обученную на synthetic benchmark results.

## 3.4. Objective score learned selector

Для training data learned selector прогоняет static topology strategies на synthetic graphs и выбирает лучшую topology по явно заданной objective function:

```text
objective_score = estimated_latency_with_overhead + 0.05 * execution_cost
```

Эта формула является простой и интерпретируемой. Она не претендует на универсальную оптимальность: коэффициент cost penalty выбран как baseline для coursework experiment и может быть откалиброван на реальных traces.

Model file `results/learned_selector_model.json` содержит:

1. `selector_version`;
2. `feature_names`;
3. `objective_score_description`;
4. training samples или prototypes;
5. выбранные topology labels.

## 3.5. Benchmark metrics

В CSV сохраняются структурные, weighted, execution, quality и robustness metrics.

Основные execution metrics:

1. `execution_latency` / `latency`;
2. `execution_cost` / `cost`;
3. `coordination_overhead`;
4. `parallel_efficiency`;
5. `executor_utilization`;
6. `critical_path_latency`.

Weighted metrics:

1. `total_node_cost`;
2. `avg_node_cost`;
3. `max_node_cost`;
4. `cost_variance`;
5. `weighted_critical_path`;
6. `weighted_parallel_width`.

Quality metrics:

1. `completeness_score`;
2. `consistency_score`;
3. `synthesis_score`;
4. `dependency_coverage_score`;
5. `overall_quality_score`.

Robustness metrics:

1. `success_rate`;
2. `failed_node_count`;
3. `skipped_node_count`;
4. `retry_count_total`;
5. `fallback_count`;
6. `recovery_success_rate`;
7. `wasted_work_estimate`.

Learned selector integration fields:

1. `selector_mode`;
2. `selected_topology`;
3. `learned_model_used`;
4. `objective_score`.

## 3.6. Интерпретация результатов

Результаты benchmark следует анализировать по `benchmark_summary.csv`. Важны не только средние latency, но и то, какая topology была фактически выбрана adaptive режимом. Например, adaptive strategy может быть структурно разумной, но проигрывать другой static topology из-за coordination overhead или особенностей synthetic cost distribution.

В финальной версии работы не утверждается, что learned selector всегда лучше static или cost-aware strategies. Learned selector является baseline, который демонстрирует возможность использовать накопленные benchmark traces для выбора topology. Его качество зависит от representativeness training graphs, objective score и объема synthetic data.

## 3.7. Quality evaluation

Quality evaluation реализована как deterministic heuristic model. Она не оценивает семантическую правильность текста, потому что в проекте используются mock agents без real LLM backend. Вместо этого evaluator анализирует execution trace и DAG:

1. выполнены ли все expected nodes;
2. есть ли failed, timeout, skipped или empty results;
3. присутствует ли synthesis/aggregate node;
4. соблюдены ли dependency constraints;
5. не использовались ли fallback results.

Fallback может повышать robustness, но снижать consistency score, потому что fallback result менее информативен, чем нормальный результат агента.

## 3.8. Failure simulation and robustness

Failure simulation моделирует synthetic exception, timeout и empty result. Recovery logic выполняет retry при exception/timeout и может использовать fallback result, если retries исчерпаны и fallback enabled. Если node не восстановлен, descendants получают статус `skipped`. Это простое и явное правило предотвращает выполнение задач с нарушенными зависимостями.

Robustness metrics позволяют сравнить стратегии не только по скорости, но и по устойчивости:

1. какая доля узлов завершилась успешно;
2. сколько узлов failed или skipped;
3. сколько retries потребовалось;
4. сколько fallback results использовано;
5. какая доля failures была восстановлена.

## 3.9. Timeline visualization

Execution traces можно визуализировать как Gantt chart:

```powershell
python run.py visualize --trace results/execution_trace.json
```

Итоговый PNG сохраняется в `results/timeline_<trace>_<topology>.png`. Timeline показывает node execution intervals по оси времени, что помогает увидеть параллельное исполнение, sequential bottlenecks, critical path duration и recovery-related gaps.

## 3.10. Reproducibility

Для воспроизводимости проект поддерживает fixed random seed, JSON config files и сохранение фактически использованной конфигурации:

```powershell
python run.py experiment --config configs/experiment_default.json --runs 5 --random-seed 7 --output-dir results/reproducible_run
```

После запуска в output directory сохраняются:

1. `benchmark_results.csv`;
2. `benchmark_summary.csv`;
3. `experiment_config_used.json`.

Unit tests также содержат reproducibility checks: benchmark с фиксированным seed запускается повторно и сравнивается по стабильным output fields.

## 3.11. Команды финального запуска

Финальная проверка проекта выполняется следующими командами:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest discover -s tests
python demo.py
python run.py benchmark --runs 1
python run.py train-selector --runs 100 --output results/learned_selector_model.json
python run.py benchmark --selector learned_adaptive --model results/learned_selector_model.json --runs 10
python run.py benchmark --selector all --model results/learned_selector_model.json --runs 10
python run.py visualize --trace results/execution_trace.json
```

Команда с `--selector all` формирует финальные CSV, содержащие static sequential, static parallel, static hierarchical, static hybrid, rule-based adaptive, cost-aware adaptive и learned adaptive results.

## 3.12. Ограничения экспериментов

Экспериментальная методика имеет ограничения:

1. используются mock agents, а не реальные LLM API;
2. synthetic graph categories упрощают реальные workflows;
3. quality evaluation является heuristic model;
4. failure simulation является synthetic robustness model;
5. learned selector является lightweight baseline и не заменяет полноценную ML-модель;
6. objective score learned selector требует калибровки на real traces перед практическим применением.
