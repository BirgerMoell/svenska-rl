# Contribute compute through your agent

The agent handles setup, execution and evidence. No paid provisioning is implicit. The contract needs only CPU
and the standard library; model baselines and training need an explicitly supplied local budget.

## L1 baseline with a local model

Any OpenAI-compatible server works (vLLM, Ollama, llama.cpp, LM Studio):

```bash
python3 -m svrl.cli rollout invoice_amount_due --base-url http://127.0.0.1:11434/v1 --model MODEL \
  --split eval --count 64 --out runs/invoice_amount_due-MODEL.jsonl
```

Record the exact model (HF commit or GGUF digest) and decoding settings in the report.

## L2/L3 training

Choose a causal LM >=100M parameters and resolve its exact Hugging Face commit
(`huggingface_hub.model_info(MODEL).sha`); check model card, license, memory and chat template. A small GRPO run
on a typed environment:

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[learn]'
python -m svrl.cli train meeting_slot --model Qwen/Qwen2.5-0.5B-Instruct --revision EXACT_HF_COMMIT \
  --steps 20 --prompts-per-step 4 --group-size 4 --eval-cases 64 --device cpu --output-dir runs/meeting-grpo
```

Use cuda/mps when available; CPU is slow. Full-parameter float32 0.5B training can need >8 GB plus activations.
Twenty steps promise nothing; inconclusive results are still useful. For real runs export data
(`svrl.cli export ENV --split train --count N --out train.jsonl`) to an RLVR trainer (open-instruct, TRL,
verl, NeMo RL) and compare rollouts before and after with `svrl.cli compare`.

The runner saves a checkpoint and a report with before/after eval, uncertainty and reward curves. No tracking
service is used; `runs/` is ignored. Submit the small report under `evidence/<environment>/<run-id>.json`.
Larger artifacts need an explicitly authorized destination; never check model weights into Git.

Use disposable containers/VMs for others' code, with bounded resources and no host credentials or personal
files. Never attach persistent GPU runners to public fork PR events.
