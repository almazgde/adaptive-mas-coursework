# Курсовая работа

**Тема:** «Исследование адаптивной оркестрации многоагентных LLM-систем на основе графов зависимостей задач»

## Аннотация

В работе рассматривается задача выбора топологии исполнения в многоагентных LLM-системах, где сложная задача представляется направленным ациклическим графом зависимостей. Реализован исследовательский прототип, включающий DAG model, graph metrics, topology selector, execution layer, benchmark framework, CSV export и matplotlib visualization. Экспериментальная часть основана на фактических результатах из `results/benchmark_results.csv` и `results/benchmark_summary.csv`.

Главный результат работы состоит в том, что adaptive orchestration может выбирать рациональную topology для ряда структур графов, но не является универсально лучшей стратегией. На `wide_sparse` и `deep_dependency` adaptive совпал с лучшей static topology. На `layered` и `centralized_coordinator` лучшей по latency оказалась static parallel, что показывает ограничения простой эвристики.

## Содержание

1. [Введение](introduction.md)
2. [Глава 1. Теоретические основы адаптивной оркестрации](chapter_1_theory.md)
3. [Глава 2. Архитектура реализованного прототипа](chapter_2_design.md)
4. [Глава 3. Экспериментальное исследование](chapter_3_experiments.md)
5. [Заключение](conclusion.md)
6. [Список использованных источников](references.md)
7. [Приложение](appendix.md)

## Ключевые экспериментальные результаты

| Graph type | Adaptive selected | Adaptive latency | Best static | Best static latency |
|---|---|---:|---|---:|
| wide_sparse | parallel | 0.56404 | parallel | 0.56404 |
| deep_dependency | sequential | 1.84883 | sequential | 1.84883 |
| layered | hybrid | 0.67070 | parallel | 0.641033 |
| centralized_coordinator | hierarchical | 0.66837 | parallel | 0.541673 |

## Использованные данные

В тексте работы использованы только материалы реализованного проекта:

1. исходный код `adaptive_mas` и `experiments`;
2. `README.md`;
3. `results/benchmark_results.csv`;
4. `results/benchmark_summary.csv`;
5. сгенерированные графики в `results/*.png`.
