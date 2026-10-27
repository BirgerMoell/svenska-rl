# Leverantörsofferter

Choose a supplier for one complete order using Swedish requirements and three
synthetic quotes. Compare total cost including one shipping charge, delivery
deadline, capacity and budget. Decline all offers if none is feasible. Resolve
equal costs by earliest delivery, then alphabetical supplier name.

## Generate and run

```bash
python3 -m svrl.cli demo supplier_quotes --seed 42
python3 -m svrl.cli check supplier_quotes
python3 -m svrl.cli smoke supplier_quotes --output runs/supplier-quotes-l1.json
```

Four terminal actions: order from Alfa, Beta or Gamma, or decline. Their positions
are shuffled, so the reference action varies. Reward is 1 for the unique correct
decision, otherwise 0. No order is placed outside the simulator.

## Data and coverage

Original synthetic data, Apache-2.0. No external datasets, real suppliers,
personal data or external services. Quantity 5–100, ordinary delivery deadline
2–14 days, unit prices 100–25,000 öre, shipping 0–30,000 öre and capacity 1–150.
Five generation modes include two ordinary random modes, universally late
offers, exact budget/deadline/capacity boundaries and tied feasible prices.
Modes share training and evaluation distributions, using independent split RNGs.

Prices are integer öre excluding VAT; do not add VAT. A complete order must use
one supplier. Capacity, budget and deadline comparisons are inclusive. Shipping
is charged once. No partial fulfillment, discount, recurring delivery or currency
conversion is modeled. Equal prices do not make the answer ambiguous because
the tie-break rules are explicit.

## Verification and evaluation

The reference solver filters feasible quotes and minimizes the specified ordered
criteria. Independent domain tests parse model-visible Swedish text, use decimal
arithmetic and separate sorting logic, and check 500 seeds per split. Hand-built
cases cover cheap-but-late, insufficient capacity, shipping, one-öre overruns,
exact boundaries, ties and refusing every offer. Every wrong action is rejected.

L1 uses the bundled tiny neural policy on CPU. It is a smoke test, not evidence
of learning. L2 and L3 are pending. The existing `svrl train supplier_quotes`
runner can train a pinned >=100M causal LM using this environment's reward and
compare pre/post accuracy on held-out seeds. See `docs/compute.md` and
`docs/validation.md`; no training was performed for this contribution.

Limitation: held-out seeds test new generated instances, not unseen templates,
supplier names, or rules. Broader generalization needs additional eval suites.
