"""Small, dependency-light GRPO for typed environments: evidence that an environment teaches (L2/L3).

For each training prompt the policy samples a group of free-form completions; the environment scores each one;
advantages are the group-normalised rewards (no critic, no KL term); the loss is the token-mean negative
log-likelihood of each completion weighted by its advantage. Groups where every completion scores the same carry
no signal and are skipped. Before/after evaluation is greedy on the same held-out eval seeds, so the comparison
is paired (docs/validation.md). For serious runs export the data (`svrl.cli export`) to a full RLVR trainer.
Tool episodes are not trained here; use `svrl.rollout` with an external multi-turn trainer.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from svrl.core import load
from svrl.validation import paired_bootstrap, qualify, save_report


def group_advantages(rewards: list, eps: float = 1e-6) -> list:
    """GRPO advantages: (r - mean) / std within one prompt's group; all zero when the group has no variance."""
    mean = sum(rewards) / len(rewards)
    std = math.sqrt(sum((r - mean) ** 2 for r in rewards) / len(rewards))
    if std < eps:
        return [0.0] * len(rewards)
    return [(r - mean) / std for r in rewards]


def train(environment_id, model_id, revision, output_dir, steps=20, prompts_per_step=4, group_size=4,
          max_new_tokens=384, eval_cases=64, learning_rate=1e-6, temperature=1.0, seed=42, device="cpu",
          threads=2):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if steps < 2 or prompts_per_step < 1 or group_size < 2 or eval_cases < 32:
        raise ValueError("need >=2 steps, >=1 prompt per step, group size >=2 and >=32 evaluation cases")
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning rate must be finite and positive")
    if not revision or revision == "main":
        raise ValueError("pin a model revision (prefer the exact HF commit)")
    env = load(environment_id)
    if env.interaction != "typed_answer":
        raise ValueError("the built-in trainer handles typed_answer environments; export tool episodes instead")
    contract = qualify(environment_id, 30)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, trust_remote_code=False).to(device)
    parameters = sum(p.numel() for p in model.parameters())
    if parameters < 100_000_000:
        raise ValueError("L2 requires >=100M model parameters")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    def prompt_ids(text):
        messages = [{"role": "user", "content": text}]
        rendered = (tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    if tokenizer.chat_template else text + "\n")
        ids = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).input_ids.to(device)
        if ids.shape[1] > 4096:
            raise ValueError("prompt exceeds the 4096-token budget")
        return ids

    def generate(ids, n, greedy):
        with torch.no_grad():
            out = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=not greedy,
                                 temperature=None if greedy else temperature, top_p=None, top_k=None,
                                 num_return_sequences=n, pad_token_id=tokenizer.pad_token_id)
        return [o[ids.shape[1]:] for o in out]

    def evaluate(seeds):
        model.eval()
        rows = []
        for s in seeds:
            env.reset(s, "eval")
            completion = tokenizer.decode(generate(prompt_ids(env.public_prompt()), 1, True)[0],
                                          skip_special_tokens=True)
            rows.append({"seed": s, "reward": env.step(completion)["reward"]})
        return rows

    evaluation_seeds = list(range(eval_cases))
    before = evaluate(evaluation_seeds)  # fixed, predeclared held-out set; never used for selection
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    start_weight = next(model.parameters()).detach().clone()
    curve = []
    for step in range(steps):
        optimizer.zero_grad()
        losses, rewards, used = [], [], 0
        for k in range(prompts_per_step):
            train_seed = seed * 1_000_000 + step * prompts_per_step + k
            env.reset(train_seed, "train")
            ids = prompt_ids(env.public_prompt())
            model.eval()
            completions = generate(ids, group_size, False)
            group = []
            for c in completions:
                env.reset(train_seed, "train")
                group.append(env.step(tokenizer.decode(c, skip_special_tokens=True))["reward"])
            rewards += group
            advantages = group_advantages(group)
            if not any(advantages):
                continue
            used += 1
            model.train()
            for completion, advantage in zip(completions, advantages):
                if advantage == 0 or completion.numel() == 0:
                    continue
                full = torch.cat([ids[0], completion]).unsqueeze(0)
                logits = model(full).logits[0, ids.shape[1] - 1:-1]
                logp = torch.log_softmax(logits.float(), -1).gather(1, completion.unsqueeze(1)).squeeze(1)
                loss = -advantage * logp.mean() / (prompts_per_step * group_size)
                if not torch.isfinite(loss):
                    raise ValueError("non-finite loss")
                loss.backward()
                losses.append(float(loss.detach()))
        norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)) if losses else 0.0
        if not math.isfinite(norm):
            raise ValueError("non-finite gradient norm")
        if losses:
            optimizer.step()
        row = {"step": step + 1, "loss": sum(losses), "reward": sum(rewards) / len(rewards),
               "groups_with_signal": used, "gradient_norm": norm}
        curve.append(row)
        print(row, flush=True)
    changed = not torch.equal(start_weight, next(model.parameters()).detach())
    after = evaluate(evaluation_seeds)
    model.save_pretrained(output / "checkpoint", safe_serialization=True)
    tokenizer.save_pretrained(output / "checkpoint")
    digest = hashlib.sha256()
    for path in sorted((output / "checkpoint").rglob("*")):
        if path.is_file():
            digest.update(path.name.encode())
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
    stats = paired_bootstrap(before, after)
    trained = changed and any(r["gradient_norm"] > 0 for r in curve)
    improved = trained and stats["delta"] >= .05 and stats["ci95"][0] > 0
    return save_report(output / "report.json", {
        "level": "L3" if improved else "L2" if trained else "L1", "status": "passed" if trained else "no_update",
        "environment": environment_id, "contract": contract, "model": model_id, "revision": revision,
        "resolved_revision": getattr(model.config, "_commit_hash", None), "parameters": parameters,
        "algorithm": "GRPO (group-normalised rewards, no KL, token-mean loss)",
        "config": {"steps": steps, "prompts_per_step": prompts_per_step, "group_size": group_size,
                   "max_new_tokens": max_new_tokens, "eval_cases": eval_cases, "learning_rate": learning_rate,
                   "temperature": temperature, "seed": seed, "device": device, "threads": threads},
        "runtime": {"torch": torch.__version__, "transformers": transformers.__version__},
        "weights_changed": changed, "checkpoint_sha256": digest.hexdigest(), "training_curve": curve,
        "before": before, "after": after, "paired_improvement": stats,
        "l3_outcome": "passed" if improved else "inconclusive",
        "limitations": "Public held-out seeds; independent replication required for trusted promotion."})
