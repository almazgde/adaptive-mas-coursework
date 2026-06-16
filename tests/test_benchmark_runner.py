import csv
import tempfile
import unittest
from pathlib import Path

from adaptive_mas.execution import FailureSimulationConfig
from adaptive_mas.topology import AdaptiveTopologyMode, TopologyType
from experiments.benchmarks.runner import BenchmarkRunner


class BenchmarkRunnerTest(unittest.TestCase):
    REQUIRED_COLUMNS = {
        "graph_type",
        "strategy",
        "selected_topology",
        "latency",
        "cost",
        "overall_quality_score",
        "success_rate",
        "selector_mode",
        "learned_model_used",
        "objective_score",
    }

    def test_benchmark_one_run_creates_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = self._runner(temp_dir)

            runner.run_all()

            self.assertTrue((Path(temp_dir) / "benchmark_results.csv").exists())
            self.assertTrue((Path(temp_dir) / "benchmark_summary.csv").exists())

    def test_csv_contains_required_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = self._runner(temp_dir)
            runner.run_all()

            with open(Path(temp_dir) / "benchmark_results.csv", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertTrue(self.REQUIRED_COLUMNS.issubset(reader.fieldnames))

    def test_fixed_seed_is_reproducible(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = self._runner(first_dir).run_all()
            second = self._runner(second_dir).run_all()

            self.assertEqual([item.__dict__ for item in first], [item.__dict__ for item in second])

    def _runner(self, output_dir):
        return BenchmarkRunner(
            runs=1,
            node_count=8,
            graph_types=["layered"],
            static_topologies=[TopologyType.SEQUENTIAL],
            adaptive_modes=[AdaptiveTopologyMode.COST_AWARE],
            output_dir=Path(output_dir),
            failure_config=FailureSimulationConfig(random_seed=11),
        )


if __name__ == "__main__":
    unittest.main()
