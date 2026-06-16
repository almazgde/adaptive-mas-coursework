# Курсовая работа

**Тема:** "Исследование адаптивной оркестрации многоагентных LLM-систем на основе графов зависимостей задач"

## Аннотация

В работе рассматривается задача выбора топологии исполнения в многоагентных LLM-системах, где сложная задача представляется направленным ациклическим графом зависимостей. Реализован исследовательский прототип, включающий DAG model, graph metrics, weighted metrics, topology selector, execution layer, benchmark framework, quality evaluation, failure simulation, CLI, CSV export и matplotlib visualizations.

Экспериментальная часть строится на воспроизводимых synthetic benchmark graphs и результатах, сохраняемых в `results/benchmark_results.csv` и `results/benchmark_summary.csv`. Текущая версия сравнивает static topologies, rule-based adaptive selector, cost-aware adaptive selector и learned adaptive selector. Learned selector является lightweight baseline на основе synthetic benchmark data, а не полноценной ML-моделью.

Главный результат работы состоит в том, что выбор topology должен учитывать не только структуру DAG, но и стоимость узлов, critical path, coordination overhead, качество результата и устойчивость к отказам. Adaptive strategies могут выбирать рациональную topology для разных графов, однако ни один selector не заявляется как универсально лучший для всех сценариев.

## Содержание

1. [Введение](introduction.md)
2. [Глава 1. Теоретические основы адаптивной оркестрации](chapter_1_theory.md)
3. [Глава 2. Архитектура реализованного прототипа](chapter_2_design.md)
4. [Глава 3. Экспериментальное исследование](chapter_3_experiments.md)
5. [Заключение](conclusion.md)
6. [Список использованных источников](references.md)
7. [Приложение](appendix.md)

## Актуальные экспериментальные результаты

Финальные численные результаты не дублируются в тексте вручную, чтобы избежать расхождения с кодом. После запуска benchmark актуальные таблицы находятся в:

1. `results/benchmark_results.csv` - сырые результаты по каждому запуску;
2. `results/benchmark_summary.csv` - агрегированные результаты по graph type, selector mode и selected topology;
3. `results/learned_selector_model.json` - сохраненная модель learned selector, если выполнялась команда обучения;
4. `results/*.png` - графики latency, efficiency, critical path impact и execution timeline.

Финальный benchmark должен включать следующие режимы:

1. static `sequential`;
2. static `parallel`;
3. static `hierarchical`;
4. static `hybrid`;
5. `rule_based_adaptive`;
6. `cost_aware_adaptive`;
7. `learned_adaptive`.

## Использованные данные

В тексте работы используются материалы реализованного проекта:

1. исходный код `adaptive_mas`, `experiments`, `run.py` и visualization scripts;
2. `README.md`;
3. `results/benchmark_results.csv`;
4. `results/benchmark_summary.csv`;
5. `results/learned_selector_model.json`;
6. сгенерированные графики и timeline visualizations в `results/`.

## Актуализация версии проекта

Текущая версия проекта включает:

1. `cost_aware_adaptive` selector, который оценивает latency, overhead и critical path penalty для всех topology candidates;
2. `learned_adaptive` selector, обучаемый на synthetic benchmark data без тяжелых ML-зависимостей;
3. weighted graph metrics, включая weighted critical path и weighted parallel width;
4. Gantt chart / execution timeline visualization на основе execution traces;
5. heuristic quality evaluation layer;
6. synthetic failure simulation and recovery logic;
7. robustness metrics для retry, fallback, failed и skipped nodes;
8. единый CLI `run.py` и JSON config files в `configs/`;
9. unit tests и reproducibility checks.

## How to reproduce experiments

Рекомендуемая последовательность финальной проверки:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest discover -s tests
python demo.py
python run.py benchmark --runs 1
python run.py train-selector --runs 100 --output results/learned_selector_model.json
python run.py benchmark --selector learned_adaptive --model results/learned_selector_model.json --runs 10
python run.py benchmark --selector all --model results/learned_selector_model.json --runs 10
python run.py visualize --trace results/execution_trace.json
```

Для воспроизводимого запуска через config:

```powershell
python run.py experiment --config configs/experiment_default.json --runs 5 --random-seed 7 --output-dir results/reproducible_run
```

Ожидаемые output files:

1. `benchmark_results.csv`;
2. `benchmark_summary.csv`;
3. `experiment_config_used.json`;
4. `learned_selector_model.json`, если запускалось обучение;
5. `timeline_<trace>_<topology>.png`, если строилась timeline visualization.

## Ограничения

Результаты следует интерпретировать как исследование orchestration layer, а не как измерение реальных LLM API:

1. используются mock agents;
2. графы являются synthetic graphs;
3. quality evaluation является heuristic model;
4. failure simulation and robustness model являются synthetic;
5. learned selector является lightweight nearest-neighbor baseline и требует калибровки на реальных traces для практического применения.
