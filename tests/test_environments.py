import json
import re
import unittest

from svrl.core import ACTIONS, load, manifests, source_digest
from svrl.validation import paired_bootstrap, validate


def v01_manifests():
    """Contract v0.1 (four-action multiple choice); v0.2 is covered by tests/test_contract_v02.py."""
    return [m for m in manifests() if m.get('contract', '0.1') == '0.1']


class EnvironmentTests(unittest.TestCase):
    def test_contract_all_discovered_environments(self):
        for manifest in v01_manifests():
            with self.subTest(environment=manifest['id']):
                self.assertEqual(validate(manifest['id'])['status'], 'passed')

    def test_invoice_domain_independently(self):
        env = load('invoice_totals')
        for seed in range(300):
            obs = env.reset(seed, 'eval')
            rows = re.findall(r'(\d+) st à (\d+),(\d+) kr', obs['instruction'])
            subtotal = sum(int(q) * (int(kr) * 100 + int(ore)) for q, kr, ore in rows)
            rate = int(re.search(r'Momsen är (\d+) procent', obs['instruction'])[1])
            total = subtotal + subtotal * rate // 100
            action = next(k for k, v in obs['actions'].items()
                          if int(v.split(',')[0]) * 100 + int(v.split(',')[1][:2]) == total)
            self.assertEqual(env.step(action)['reward'], 1)

    def test_calendar_domain_independently(self):
        env = load('calendar_booking')
        for seed in range(300):
            obs = env.reset(seed, 'eval')
            busy = set()
            for line in obs['instruction'].splitlines()[1:]:
                busy.update(re.findall(r'\d\d:\d\d', line))
            free = [f'{hour:02d}:{minute:02d}' for hour in range(8, 16)
                    for minute in (0, 30) if f'{hour:02d}:{minute:02d}' not in busy]
            action = next(k for k, v in obs['actions'].items() if v == free[0])
            self.assertEqual(env.step(action)['reward'], 1)

    def test_inventory_domain_minimality_and_pack_size(self):
        env = load('inventory_order')
        observed_zero = False
        for seed in range(300):
            obs = env.reset(seed, 'eval')
            stock, reserved, target, pack = map(int, re.findall(r'\d+', obs['instruction']))
            # Enumerate legal purchases rather than reusing the generator's formula.
            expected = next(n for n in range(0, 1000, pack) if stock - reserved + n >= target)
            observed_zero |= expected == 0
            action = next(k for k, v in obs['actions'].items() if int(v.split()[0]) == expected)
            self.assertEqual(env.step(action)['reward'], 1)
        self.assertTrue(observed_zero)

    def test_correct_action_positions_vary(self):
        for manifest in v01_manifests():
            env = load(manifest['id'])
            positions = set()
            for seed in range(100):
                env.reset(seed)
                positions.add(env.reference_action())
            self.assertEqual(positions, set(ACTIONS))

    def test_invalid_seeds_and_unknown_environments(self):
        env = load('invoice_totals')
        for seed in (-1, '1', True):
            with self.assertRaises(ValueError):
                env.reset(seed)
        with self.assertRaises(ValueError):
            env.reset(0, 'secret')
        with self.assertRaises(ValueError):
            load('../../untrusted')

    def test_public_payload_does_not_expose_private_fields(self):
        for manifest in v01_manifests():
            obs = load(manifest['id']).reset()
            self.assertNotIn('answer', json.dumps(obs))
            self.assertEqual(set(obs), {'instruction', 'actions', 'max_steps'})

    def test_source_digest_is_stable(self):
        self.assertEqual(source_digest(), source_digest())
        self.assertEqual(len(source_digest()), 64)


class EvaluationTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
