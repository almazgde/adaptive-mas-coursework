# Testing

The test suite uses the Python standard library `unittest`; no internet, API keys, or external services are required.

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run All Tests

```bash
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest discover -s tests
```

On macOS/Linux:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests
```

## Run One Test Module

```bash
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest tests.test_benchmark_runner
```

## Reproducibility Check

The benchmark tests run the same fixed-seed configuration twice and compare the resulting dataclass rows:

```bash
$env:PYTHONDONTWRITEBYTECODE='1'; python -m unittest tests.test_benchmark_runner.BenchmarkRunnerTest.test_fixed_seed_is_reproducible
```

You can also run a small deterministic experiment manually:

```bash
python run.py benchmark --runs 1 --node-count 8 --graph layered --selector cost_aware --output-dir results/repro_smoke --random-seed 11
```
