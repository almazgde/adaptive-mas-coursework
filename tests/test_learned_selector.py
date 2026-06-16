import tempfile
import unittest
from pathlib import Path

import run
from adaptive_mas.topology import AdaptiveTopologyMode, LearnedTopologySelector, TopologyType
from adaptive_mas.topology.learned_selector import FEATURE_NAMES
from experiments.benchmarks.runner import BenchmarkRunner
from experiments.benchmarks.synthetic_graphs import SyntheticGraphFactory


class LearnedSelectorTest(unittest.TestCase):
    def test_feature_extraction_has_stable_names(self):
        dag = SyntheticGraphFactory.layered(node_count=8, seed=1)

        features = LearnedTopologySelector.extract_features(dag)

        self.assertEqual(list(features), FEATURE_NAMES)

    def test_train_small_dataset_and_predict_valid_topology(self):
        selector = LearnedTopologySelector.train(["wide_sparse", "deep_dependency"], runs=2, node_count=8)
        dag = SyntheticGraphFactory.wide_sparse(node_count=8, seed=3)

        prediction = selector.predict(dag)

        self.assertIsInstance(prediction.topology, TopologyType)
        self.assertGreaterEqual(prediction.objective_score, 0.0)

    def test_model_save_load(self):
        selector = LearnedTopologySelector.train(["layered"], runs=1, node_count=8)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.json"

            selector.save(path)
            loaded = LearnedTopologySelector.load(path)

            self.assertEqual(len(loaded.samples), len(selector.samples))
            self.assertEqual(loaded.feature_names, selector.feature_names)

    def test_missing_model_has_clear_error(self):
        with self.assertRaises(FileNotFoundError):
            LearnedTopologySelector.load(Path("missing_learned_selector_model.json"))

    def test_empty_model_has_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty_model.json"
            path.write_text('{"feature_names": [], "training_samples": []}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "no training samples"):
                LearnedTopologySelector.load(path)

    def test_cli_requires_model_for_learned_selector(self):
        config = run.apply_overrides(run.DEFAULT_CONFIG, run.build_parser().parse_args(["benchmark", "--selector", "learned_adaptive"]))

        with self.assertRaisesRegex(ValueError, "requires --model"):
            run.validate_config(config)

    def test_benchmark_can_use_learned_selector_model(self):
        selector = LearnedTopologySelector.train(["layered"], runs=1, node_count=8)
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.json"
            selector.save(model_path)
            runner = BenchmarkRunner(
                runs=1,
                node_count=8,
                graph_types=["layered"],
                static_topologies=[],
                adaptive_modes=[AdaptiveTopologyMode.LEARNED],
                output_dir=Path(temp_dir),
                learned_model_path=model_path,
            )

            results = runner.run_all()

            self.assertEqual(results[0].selector_mode, "learned_adaptive")
            self.assertEqual(results[0].learned_model_used, str(model_path))
            self.assertGreaterEqual(results[0].objective_score, 0.0)


if __name__ == "__main__":
    unittest.main()
