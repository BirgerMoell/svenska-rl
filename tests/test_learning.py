import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('torch'), 'optional torch not installed')
class PolicyGradientTests(unittest.TestCase):
    def test_rewarded_action_increases_and_failed_action_decreases(self):
        import torch
        from svrl.learning import policy_gradient_loss
        for reward in (0., 1.):
            logits = torch.nn.Parameter(torch.zeros(4))
            optimizer = torch.optim.SGD([logits], lr=.1)
            distribution = torch.distributions.Categorical(logits=logits)
            loss = policy_gradient_loss(distribution, torch.tensor(0), reward)
            self.assertTrue(torch.isfinite(loss))
            loss.backward()
            self.assertGreater(float(logits.grad.abs().sum()), 0)
            optimizer.step()
            probability = float(torch.softmax(logits.detach(), dim=-1)[0])
            self.assertGreater(probability, .25) if reward else self.assertLess(probability, .25)

    def test_smoke_rejects_inadequate_episode_count(self):
        from svrl.learning import smoke
        with self.assertRaises(ValueError):
            smoke('invoice_totals', '/tmp/unused-svrl-report.json', episodes=1)
