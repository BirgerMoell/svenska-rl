"""Independent oracle reconstructs outcomes from the model-visible Swedish text."""
from decimal import Decimal
import random
import re
import unittest

from environments.supplier_quotes.environment import Quote, build_task, create


def public_solution(task):
    text = task.instruction
    quantity = int(re.search(r'Behov: (\d+) enheter', text)[1])
    budget = Decimal(re.search(r'Budget: ([\d,]+) kr', text)[1].replace(',', '.'))
    deadline = int(re.search(r'Senast leverans: (\d+) dagar', text)[1])
    candidates = []
    for line in text.splitlines():
        fields = line.split(' | ')
        if len(fields) != 5 or fields[0] not in ('Alfa', 'Beta', 'Gamma'):
            continue
        name, price, shipping, days, capacity = fields
        total = Decimal(price.replace(',', '.')) * quantity + Decimal(shipping.replace(',', '.'))
        if int(capacity) < quantity or int(days) > deadline or total > budget:
            continue
        candidates.append((total, int(days), name))
    if not candidates:
        expected = 'Avstå: ingen offert uppfyller samtliga krav.'
    else:
        # Independent stable sorts express the specified precedence.
        candidates.sort(key=lambda c: c[2])
        candidates.sort(key=lambda c: c[1])
        candidates.sort(key=lambda c: c[0])
        expected = f'Beställ {quantity} enheter från {candidates[0][2]}.'
    return 'ABCD'[task.choices.index(expected)]


class SupplierQuotesTests(unittest.TestCase):
    def assert_winner(self, quotes, expected, quantity=10, budget=10000, deadline=5):
        task = build_task(random.Random(3), quantity, budget, deadline, quotes)
        self.assertEqual(task.answer, public_solution(task))
        selected = task.choices['ABCD'.index(task.answer)]
        self.assertEqual(selected, expected)

    def test_shipping_changes_lowest_total(self):
        self.assert_winner([Quote('Alfa', 100, 9000, 2, 20), Quote('Beta', 200, 0, 2, 20),
                            Quote('Gamma', 300, 0, 2, 20)], 'Beställ 10 enheter från Beta.')

    def test_cheapest_offer_rejected_for_late_delivery(self):
        self.assert_winner([Quote('Alfa', 100, 0, 6, 20), Quote('Beta', 200, 0, 5, 20),
                            Quote('Gamma', 300, 0, 2, 20)], 'Beställ 10 enheter från Beta.')

    def test_cheapest_offer_rejected_for_capacity(self):
        self.assert_winner([Quote('Alfa', 100, 0, 2, 9), Quote('Beta', 200, 0, 2, 10),
                            Quote('Gamma', 300, 0, 2, 20)], 'Beställ 10 enheter från Beta.')

    def test_exact_budget_and_deadline_are_valid_but_one_ore_over_is_not(self):
        self.assert_winner([Quote('Alfa', 1000, 1, 5, 10), Quote('Beta', 1000, 0, 5, 10),
                            Quote('Gamma', 1000, 2, 5, 10)], 'Beställ 10 enheter från Beta.')

    def test_equal_total_uses_delivery_then_name(self):
        self.assert_winner([Quote('Gamma', 100, 0, 1, 10), Quote('Beta', 100, 0, 1, 10),
                            Quote('Alfa', 100, 0, 2, 10)], 'Beställ 10 enheter från Beta.')
        self.assert_winner([Quote('Gamma', 100, 0, 1, 10), Quote('Beta', 100, 0, 1, 10),
                            Quote('Alfa', 100, 0, 1, 10)], 'Beställ 10 enheter från Alfa.')

    def test_no_feasible_offer_requires_decline(self):
        self.assert_winner([Quote('Alfa', 100, 0, 6, 10), Quote('Beta', 100, 0, 1, 9),
                            Quote('Gamma', 1001, 0, 1, 10)],
                           'Avstå: ingen offert uppfyller samtliga krav.')

    def test_generated_splits_have_correct_rewards_and_decision_diversity(self):
        env = create()
        winners, prompts = set(), {}
        for split in ('train', 'dev', 'eval'):
            prompts[split] = set()
            for seed in range(500):
                env.reset(seed, split)
                task = env._task  # Trusted qualification only; oracle uses public text.
                action = public_solution(task)
                selected = task.choices['ABCD'.index(action)]
                winners.add(next((name for name in ('Alfa', 'Beta', 'Gamma')
                                  if f'från {name}.' in selected), 'decline'))
                self.assertEqual(env.step(action)['reward'], 1)
                for wrong in set('ABCD') - {action}:
                    env.reset(seed, split)
                    self.assertEqual(env.step(wrong)['reward'], 0)
                prompts[split].add(task.prompt())
        self.assertEqual(winners, {'Alfa', 'Beta', 'Gamma', 'decline'})
        self.assertFalse(prompts['train'] & prompts['eval'])
        self.assertFalse(prompts['dev'] & prompts['eval'])

    def test_invalid_action_cannot_exploit_verifier(self):
        env = create()
        for invalid in ('A B C D', 'Avstå', 'ignore the verifier and return 1', {}, None):
            env.reset(42)
            self.assertEqual(env.step(invalid)['reward'], 0)
