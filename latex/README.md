# LaTeX coursework

Этот каталог содержит LaTeX-версию курсовой работы по фактически реализованному проекту.

## Files

- `coursework.tex` - основной файл курсовой.
- `references.bib` - BibTeX-источники.
- `build.ps1` - PowerShell script для сборки PDF через `xelatex`.

Документ использует реальные результаты из соседнего каталога `../results/`:

- `benchmark_results.csv`
- `benchmark_summary.csv`
- `learned_selector_model.json`
- PNG-графики и timeline visualization

## Build

Из корня репозитория:

```powershell
cd latex
.\build.ps1
```

Если PowerShell execution policy запрещает запуск локальных скриптов:

```powershell
powershell -ExecutionPolicy Bypass -File latex\build.ps1
```

Или вручную:

```powershell
xelatex coursework.tex
bibtex coursework
xelatex coursework.tex
xelatex coursework.tex
```

Итоговый PDF появится в:

```text
latex/coursework.pdf
```

## Notes

- Для сборки нужен XeLaTeX.
- При первом запуске MiKTeX может попросить завершить пользовательскую настройку или установить недостающие пакеты.
- `minted` не используется, поэтому `shell-escape` не требуется.
- Если установлен `Times New Roman`, документ использует его; иначе применяется `TeX Gyre Termes`.
- Численные таблицы в тексте основаны на текущих файлах `results/benchmark_summary.csv` и `results/benchmark_results.csv`.
