# Contribute compute through your agent

The agent handles setup, execution and evidence. No paid provisioning is implicit.
CPU workers can run L1. Model training needs an explicitly supplied local budget.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[learn]'
python -m svrl.cli smoke invoice_totals --output runs/invoice-l1.json
```

For L2/L3 choose a causal LM >=100M parameters and resolve its exact Hugging Face
commit. A candidate is `Qwen/Qwen2.5-0.5B-Instruct`; check model card, license,
memory and tokenizer compatibility. Resolve via `huggingface_hub.model_info(MODEL).sha`.

```bash
python -m svrl.cli train invoice_totals \
  --model Qwen/Qwen2.5-0.5B-Instruct --revision EXACT_HF_COMMIT \
  --steps 20 --batch-size 4 --eval-cases 64 \
  --learning-rate 0.00001 --device cpu --threads 2 \
  --output-dir runs/invoice-experiment
```

Replace EXACT_HF_COMMIT with the resolved commit. Use cuda/mps only if supported.
Full-parameter float32 0.5B training can need >8 GB plus activations; check capacity
before launch. CPU may be slow. Twenty steps do not promise improved arithmetic.
Inconclusive results remain useful.

The runner saves a checkpoint and report with before/after eval, uncertainty and
loss/reward curves. No tracking service is used. `runs/` is ignored. Submit the small
report under `evidence/<environment>/<run-id>.json` in a PR. Larger artifacts need
an explicitly authorized destination; never check model weights into Git.

Use disposable containers/VMs for others' code, with bounded resources and no host
credentials or personal files. Never attach persistent GPU runners to public fork
PR events. Shared scheduling and trusted evidence ingestion are roadmap items.
