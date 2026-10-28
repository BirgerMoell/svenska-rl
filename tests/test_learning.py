import json
import tempfile
import unittest
from pathlib import Path

from svrl.learning import group_advantages
from svrl.rollout import compare_files
from svrl.validation import paired_bootstrap


class GroupAdvantageTests(unittest.TestCase):
    def test_better_completions_get_positive_advantage(self):
        adv = group_advantages([1.0, 0.0, 0.0, 1.0])
        self.assertEqual(adv, [1.0, -1.0, -1.0, 1.0])
        self.assertAlmostEqual(sum(group_advantages([0.2, 0.5, 0.9])), 0.0)

    def test_groups_without_variance_carry_no_signal(self):
        self.assertEqual(group_advantages([1.0, 1.0, 1.0]), [0.0, 0.0, 0.0])
        self.assertEqual(group_advantages([0.0, 0.0]), [0.0, 0.0])


class PairedEvaluationTests(unittest.TestCase):
    def test_bootstrap_reports_improvement_and_no_change(self):
        before = [{'seed': n, 'reward': 0.0} for n in range(32)]
        after = [{'seed': n, 'reward': 1.0} for n in range(32)]
        self.assertEqual(paired_bootstrap(before, after), {'delta': 1, 'ci95': [1, 1]})
        self.assertEqual(paired_bootstrap(before, before), {'delta': 0, 'ci95': [0, 0]})

    def test_mismatched_evaluation_rejected(self):
        before = [{'seed': 1, 'reward': 0}, {'seed': 2, 'reward': 0}]
        after = [{'seed': 2, 'reward': 1}, {'seed': 3, 'reward': 1}]
        with self.assertRaises(ValueError):
            paired_bootstrap(before, after)

    def test_compare_rollout_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            def write(name, rewards):
                path = Path(tmp) / name
                path.write_text("".join(json.dumps({"env": "meeting_slot", "split": "eval", "seed": i, "reward": r}) + "\n"
                                        for i, r in enumerate(rewards)))
                return str(path)
            before = write("before.jsonl", [0.0] * 20 + [1.0] * 20)
            after = write("after.jsonl", [1.0] * 40)
            report = compare_files(before, after)
            self.assertEqual(report["l3_outcome"], "passed")
            self.assertEqual(compare_files(before, before)["l3_outcome"], "inconclusive")
            failed = Path(tmp) / "failed.jsonl"
            failed.write_text(json.dumps({"env": "meeting_slot", "split": "eval", "seed": 0, "reward": None}) + "\n")
            with self.assertRaises(ValueError):
                compare_files(str(failed), after)


if __name__ == '__main__':
    unittest.main()
