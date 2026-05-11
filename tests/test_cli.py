import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run


class CliSmokeTest(unittest.TestCase):
    def test_cli_demo_dispatches_without_error(self):
        with patch("demo.run_scenario") as run_scenario:
            exit_code = run.main(["demo", "--scenario", "wide_sparse"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_scenario.call_count, 1)

    def test_cli_benchmark_runs_one_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code = run.main(
                [
                    "benchmark",
                    "--runs",
                    "1",
                    "--node-count",
                    "6",
                    "--graph",
                    "layered",
                    "--selector",
                    "cost_aware",
                    "--output-dir",
                    temp_dir,
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / "benchmark_results.csv").exists())
            self.assertTrue((Path(temp_dir) / "benchmark_summary.csv").exists())
            self.assertTrue((Path(temp_dir) / "experiment_config_used.json").exists())

    def test_cli_experiment_runs_from_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "experiment.json"
            output_dir = Path(temp_dir) / "out"
            config_path.write_text(
                json.dumps(
                    {
                        "runs": 1,
                        "node_count": 6,
                        "graph_types": ["layered"],
                        "selector_mode": "rule_based",
                        "output_dir": str(output_dir),
                    }
                ),
                encoding="utf-8",
            )

            exit_code = run.main(["experiment", "--config", str(config_path)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "benchmark_results.csv").exists())

    def test_cli_train_selector_creates_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"

            exit_code = run.main(["train-selector", "--runs", "1", "--node-count", "6", "--output", str(model_path)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(model_path.exists())

    def test_config_file_is_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "experiment.json"
            config_path.write_text(json.dumps({"runs": 3, "graph_types": ["layered"]}), encoding="utf-8")

            config = run.load_config(config_path)

            self.assertEqual(config["runs"], 3)
            self.assertEqual(config["graph_types"], ["layered"])

    def test_command_line_overrides_config_values(self):
        parser = run.build_parser()
        args = parser.parse_args(
            [
                "experiment",
                "--config",
                "configs/experiment_default.json",
                "--runs",
                "2",
                "--graph",
                "deep_dependency",
                "--selector",
                "rule_based",
            ]
        )
        config = run.apply_overrides({"runs": 10, "graph_types": ["layered"]}, args)

        self.assertEqual(config["runs"], 2)
        self.assertEqual(config["graph_types"], ["deep_dependency"])
        self.assertEqual(config["selector_mode"], "rule_based")


if __name__ == "__main__":
    unittest.main()
