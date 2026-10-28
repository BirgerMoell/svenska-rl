import json
from collections import Counter
import re
import unittest

from svrl.core import ROOT


class CatalogueTests(unittest.TestCase):
    def test_queue_has_distinct_tasks_across_all_work_areas(self):
        tasks = json.loads((ROOT / 'catalogue/tasks.json').read_text())
        taxonomy = json.loads((ROOT / 'catalogue/taxonomy.json').read_text())
        self.assertGreaterEqual(len(tasks), 100)
        self.assertEqual(len({t['id'] for t in tasks}), len(tasks))
        self.assertEqual(len({t['title'] for t in tasks}), len(tasks))
        counts = Counter(t['area'] for t in tasks)
        self.assertEqual(set(counts), {a['id'] for a in taxonomy['areas']})
        self.assertTrue(all(count >= 5 for count in counts.values()))
        urls = [t['issue_url'] for t in tasks if t.get('issue_url')]
        self.assertEqual(len(urls), len(set(urls)))
        for task in tasks:
            with self.subTest(task=task['id']):
                self.assertRegex(task['id'], r'^[a-z0-9_-]+$')
                self.assertTrue(task['instructions'])
                self.assertGreaterEqual(len(task['acceptance_checks']), 5)
                self.assertTrue((ROOT / task['contract']).is_file())
                if task['status'] == 'implemented':
                    self.assertTrue((ROOT / 'environments' / task['environment'] / 'manifest.json').is_file())
                self.assertTrue((ROOT / task['acceptance']).is_file())
                if task.get('issue_url'):
                    self.assertRegex(task['issue_url'], r'^https://github.com/BirgerMoell/svenska-rl/issues/\d+$')

    def test_expanded_specs_are_implementable_without_hidden_requirements(self):
        tasks = json.loads((ROOT / 'catalogue/tasks.json').read_text())
        detailed = [t for t in tasks if t.get('inputs')]
        self.assertGreaterEqual(len(detailed), 80)
        for task in detailed:
            with self.subTest(task=task['id']):
                for field in ('objective', 'verifier', 'variation', 'evaluation'):
                    self.assertTrue(task[field].strip())
                self.assertGreaterEqual(len(task['edge_cases']), 3)
                self.assertEqual(task['prerequisites'], [])
                self.assertIn(task['interaction'], ('typed_answer', 'tool_episode'))
                self.assertIn('L1', task['resources'])
