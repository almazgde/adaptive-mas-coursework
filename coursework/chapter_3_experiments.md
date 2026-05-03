# Глава 3. Экспериментальное исследование

## 3.1. Описание экспериментов

Цель экспериментов состояла в сравнении topology strategies по следующим метрикам:

1. execution latency;
2. execution cost;
3. coordination overhead;
4. parallel efficiency;
5. executor utilization;
6. critical path latency.

Данные экспериментов были сохранены в `results/benchmark_results.csv`, а агрегированная статистика — в `results/benchmark_summary.csv`. Для каждой комбинации graph type и strategy было выполнено 10 повторов. Все графы в текущем запуске имели `16` узлов. Пример строки из `benchmark_results.csv` для `wide_sparse` показывает, что в одном из запусков static sequential имел `16` узлов, `3` ребра, глубину `4`, latency `1.8472`, critical path latency `0.4177`, coordination overhead `0.0335` и executor utilization `0.981864`.

## 3.2. Synthetic graph categories

В benchmark framework использованы четыре категории синтетических графов.

**Wide sparse graphs** имеют низкую плотность зависимостей и высокий потенциальный параллелизм. В результатах для `wide_sparse` графы имеют малое число рёбер и небольшую глубину, что делает parallel execution рациональной стратегией.

**Deep dependency graphs** имеют длинный критический путь. Каждая задача зависит от предыдущей, поэтому параллелизм почти не даёт выигрыша. В таких условиях дополнительные координационные расходы могут только ухудшать latency.

**Layered graphs** имеют смешанную структуру: зависимости организованы слоями, а внутри слоя возможно параллельное исполнение. Для них естественно ожидать конкурентность между parallel и hybrid strategies.

**Centralized coordinator graphs** имеют иерархическую структуру с выделенным координатором и агрегирующими зависимостями. Такие графы проверяют, насколько hierarchical topology соответствует coordinator pattern.

Визуальные схемы категорий графов сохранены в:

1. `results/graph_wide_sparse.png`;
2. `results/graph_deep_dependency.png`;
3. `results/graph_layered.png`;
4. `results/graph_centralized_coordinator.png`.

## 3.3. Static vs adaptive comparison

В таблице 1 приведены средние задержки из `benchmark_summary.csv`.

**Таблица 1 — Средняя latency по стратегиям**

| Graph type | Strategy | Selected topology | Avg latency | Std latency |
|---|---|---|---:|---:|
| wide_sparse | adaptive | parallel | 0.56404 | 0.06124 |
| wide_sparse | static parallel | parallel | 0.56404 | 0.06124 |
| wide_sparse | static hybrid | hybrid | 0.60336 | 0.056723 |
| wide_sparse | static hierarchical | hierarchical | 0.60426 | 0.056723 |
| wide_sparse | static sequential | sequential | 1.84283 | 0.132298 |
| deep_dependency | adaptive | sequential | 1.84883 | 0.132298 |
| deep_dependency | static sequential | sequential | 1.84883 | 0.132298 |
| deep_dependency | static parallel | parallel | 1.93783 | 0.132298 |
| deep_dependency | static hybrid | hybrid | 2.02433 | 0.132298 |
| deep_dependency | static hierarchical | hierarchical | 2.07483 | 0.132298 |
| layered | adaptive | hybrid | 0.67070 | 0.040791 |
| layered | static parallel | parallel | 0.641033 | 0.040115 |
| layered | static hybrid | hybrid | 0.67070 | 0.040791 |
| layered | static hierarchical | hierarchical | 0.69090 | 0.041284 |
| layered | static sequential | sequential | 1.85433 | 0.132298 |
| centralized_coordinator | adaptive | hierarchical | 0.66837 | 0.067639 |
| centralized_coordinator | static parallel | parallel | 0.541673 | 0.054621 |
| centralized_coordinator | static hierarchical | hierarchical | 0.66837 | 0.067639 |
| centralized_coordinator | static hybrid | hybrid | 0.68247 | 0.067639 |
| centralized_coordinator | static sequential | sequential | 1.85283 | 0.132298 |

Рисунок `results/latency_comparison.png` визуализирует сравнение задержек по категориям графов и стратегиям. Рисунок `results/adaptive_vs_static.png` показывает агрегированное сравнение adaptive и static strategies.

## 3.4. Latency analysis

Для `wide_sparse` adaptive selector выбрал `parallel`, что совпало с лучшей статической стратегией. Средняя latency parallel и adaptive составила `0.56404`, тогда как sequential показал `1.84283`. Это подтверждает, что на широком разреженном графе параллельное исполнение существенно снижает задержку.

Для `deep_dependency` adaptive selector выбрал `sequential`. Это также совпало с лучшей статической стратегией: latency `1.84883`. Parallel, hybrid и hierarchical оказались медленнее из-за отсутствия достаточного параллелизма и дополнительных overhead-компонентов.

Для `layered` adaptive selector выбрал `hybrid`, что соответствует смешанной структуре графа. Однако лучшей по latency оказалась static parallel со значением `0.641033`, тогда как adaptive/hybrid имел `0.67070`. Разница невелика, но показывает, что эвристика adaptive selector не всегда выбирает минимальную latency.

Для `centralized_coordinator` adaptive selector выбрал `hierarchical`, что структурно объяснимо, поскольку граф имеет coordinator pattern. Однако static parallel показал меньшую latency `0.541673`, чем adaptive/hierarchical `0.66837`. Это означает, что наличие центрального узла само по себе не гарантирует преимущество hierarchical execution в используемой модели затрат.

## 3.5. Parallel efficiency

Parallel efficiency отражает отношение critical path latency к общей execution latency. Чем ближе значение к `1`, тем меньше потери относительно нижней границы, задаваемой критическим путём.

**Таблица 2 — Средняя parallel efficiency**

| Graph type | Strategy | Avg parallel efficiency |
|---|---|---:|
| wide_sparse | adaptive/parallel | 0.83073 |
| wide_sparse | sequential | 0.247707 |
| deep_dependency | adaptive/sequential | 0.987228 |
| deep_dependency | parallel | 0.966571 |
| layered | adaptive/hybrid | 0.80090 |
| layered | parallel | 0.850543 |
| centralized_coordinator | adaptive/hierarchical | 0.587557 |
| centralized_coordinator | parallel | 0.731375 |

Рисунок `results/topology_efficiency.png` показывает общую эффективность топологий. Наиболее важный вывод состоит в том, что высокая parallel efficiency не всегда означает лучшую стратегию в универсальном смысле: её нужно интерпретировать вместе с latency, overhead и utilization.

## 3.6. Coordination overhead

Coordination overhead моделирует дополнительные затраты на управление параллельными задачами, слоями, группами и иерархическими структурами. В таблице 3 приведены средние значения overhead.

**Таблица 3 — Средний coordination overhead**

| Graph type | Strategy | Avg coordination overhead |
|---|---|---:|
| wide_sparse | sequential | 0.0335 |
| wide_sparse | adaptive/parallel | 0.1105 |
| wide_sparse | hybrid | 0.1412 |
| deep_dependency | sequential/adaptive | 0.0395 |
| deep_dependency | parallel | 0.1285 |
| deep_dependency | hybrid | 0.2150 |
| deep_dependency | hierarchical | 0.2655 |
| layered | sequential | 0.0450 |
| layered | parallel | 0.111533 |
| layered | adaptive/hybrid | 0.1412 |
| centralized_coordinator | sequential | 0.0435 |
| centralized_coordinator | parallel | 0.113833 |
| centralized_coordinator | adaptive/hierarchical | 0.1441 |

Для `deep_dependency` overhead демонстрирует важное ограничение параллелизма: если критический путь почти равен всему графу, дополнительные механизмы координации не дают выигрыша. Для `wide_sparse` overhead parallel выше, чем у sequential, но выигрыш от параллельного исполнения значительно перекрывает эти затраты.

## 3.7. Critical path impact

Critical path задаёт нижнюю границу latency. Если граф глубокий, возможности ускорения ограничены. Рисунок `results/critical_path_impact.png` показывает связь между critical path latency и execution latency.

В `deep_dependency` critical path фактически определяет весь ход исполнения. Поэтому adaptive selector выбрал sequential, а executor utilization для adaptive/sequential составил `0.978533`. Это означает, что один исполнитель почти полностью занят, но дополнительные исполнители не используются эффективно.

В `wide_sparse` critical path значительно короче полной последовательной суммы работ. Поэтому parallel и adaptive снижают latency до `0.56404`, несмотря на overhead `0.1105`.

## 3.8. Почему adaptive не всегда быстрее static

Полученные результаты не подтверждают утверждение, что adaptive orchestration всегда быстрее static topology. Adaptive selector является эвристическим и выбирает топологию по структурным признакам DAG. Однако фактическая latency зависит не только от структуры графа, но и от модели стоимости, числа effective workers, величины overhead, распределения synthetic node costs и конкретной стратегии scheduling.

В `centralized_coordinator` adaptive выбрал hierarchical, потому что граф имеет выраженный coordinator pattern. Но static parallel оказался быстрее: `0.541673` против `0.66837`. Это показывает, что structural match не всегда равен performance optimum.

В `layered` adaptive выбрал hybrid, что логично для многослойного графа. Однако parallel был немного быстрее: `0.641033` против `0.67070`. Следовательно, adaptive selector нужно улучшать с учётом прогнозируемой стоимости исполнения, а не только graph metrics.

## 3.9. Ответы на исследовательские вопросы

**RQ1: Когда adaptive topology outperform static topology?**  
В текущих экспериментах adaptive совпал с лучшей static strategy для `wide_sparse` и `deep_dependency`, но не превзошёл лучший static baseline. Он превосходит отдельные неподходящие статические стратегии: например, на `wide_sparse` adaptive/parallel быстрее sequential (`0.56404` против `1.84283`), а на `deep_dependency` adaptive/sequential быстрее static parallel (`1.84883` против `1.93783`).

**RQ2: Как graph structure влияет на orchestration efficiency?**  
Широкие разреженные графы выигрывают от parallel execution. Глубокие графы с длинным critical path лучше исполняются sequential. Layered graphs находятся между этими случаями, а coordinator graphs требуют более точного учёта стоимости координации.

**RQ3: Когда coordination overhead становится выше пользы parallelism?**  
Это происходит, когда граф не содержит достаточного независимого параллелизма. На `deep_dependency` parallel overhead `0.1285` выше sequential/adaptive overhead `0.0395`, а latency parallel хуже sequential.

**RQ4: Как topology влияет на critical path latency?**  
Topology не устраняет зависимости critical path, но добавляет различные overhead-компоненты и меняет степень приближения total latency к critical path latency. На `deep_dependency` sequential/adaptive достигает parallel efficiency `0.987228`, тогда как на coordinator-графе hierarchical/adaptive имеет `0.587557`, а parallel — `0.731375`.

## 3.10. Ограничения эксперимента

Эксперимент имеет несколько ограничений.

Во-первых, используются mock agents, а не реальные LLM. Поэтому результаты нельзя интерпретировать как абсолютные задержки реальных API-вызовов.

Во-вторых, synthetic graph categories упрощают реальные task graphs. Реальные задачи могут иметь неоднородные зависимости, динамически возникающие подзадачи и неопределённое качество промежуточных ответов.

В-третьих, execution cost и coordination overhead рассчитываются симулятором. Такая модель полезна для сравнения стратегий внутри проекта, но требует калибровки на реальных системах.

В-четвёртых, adaptive selector основан на простой эвристике. Он интерпретируем, но не оптимизирует latency напрямую и не обучается на предыдущих запусках.
