"""Local tiny-policy smoke tests and genuine policy-gradient LM training.

All starter tasks expose four terminal actions. The HF policy samples the
single-token action A/B/C/D from the causal LM's conditional distribution.
This is constrained-action RL, not free-form generation or SFT.
"""
import hashlib
import math
from pathlib import Path

from svrl.core import ACTIONS, ROOT, load
from svrl.validation import evaluate, paired_bootstrap, save_report, validate


def policy_gradient_loss(distribution, action, reward):
    return -(reward - .25) * distribution.log_prob(action)


def smoke(environment_id, output, episodes=8):
    import subprocess
    import sys
    import torch
    if episodes < 8:
        raise ValueError("L1 needs at least eight model episodes")
    domain_tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
                                 cwd=ROOT, capture_output=True, text=True, timeout=120)
    if domain_tests.returncode:
        raise ValueError("domain/project tests failed:\n" + domain_tests.stderr)
    torch.manual_seed(42)
    model = torch.nn.Sequential(torch.nn.Linear(256, 32), torch.nn.Tanh(), torch.nn.Linear(32, 4))
    model.eval()

    def act(prompt):
        features = torch.zeros(256)
        for word in prompt.split():
            i = hashlib.sha256(word.encode()).digest()[0]
            features[i] += 1
        with torch.no_grad():
            logits = model(features / max(1, len(prompt.split())))
            if not torch.isfinite(logits).all():
                raise ValueError("non-finite model logits")
            return ACTIONS[int(logits.argmax())]

    contract = validate(environment_id)
    rows = evaluate(environment_id, act, range(episodes))
    return save_report(output, {"level": "L1", "environment": environment_id,
        "status": "passed", "contract": contract,
        "domain_tests": {"status": "passed", "command": "python -m unittest discover -s tests",
                         "summary": domain_tests.stderr.strip()},
        "policy": {"kind": "randomly_initialized_tiny_neural_policy",
                   "parameters": sum(p.numel() for p in model.parameters()), "seed": 42},
        "episodes": rows, "learning_claim": False,
        "limitations": "Smoke test only. This policy is not a pretrained Swedish language model."})


def train(environment_id, model_id, revision, output_dir, steps=20, batch_size=4,
          eval_cases=64, learning_rate=1e-5, seed=42, device="cpu", threads=2):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if steps < 2 or batch_size < 2 or eval_cases < 32:
        raise ValueError("need >=2 steps, >=2 batch size, >=32 evaluation cases")
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning rate must be finite and positive")
    if not revision or revision == "main":
        raise ValueError("pin a model revision (prefer the exact HF commit)")
    validate(environment_id)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    l1 = smoke(environment_id, output / "l1.json")
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, revision=revision, trust_remote_code=False).to(device)
    parameters = sum(p.numel() for p in model.parameters())
    if parameters < 100_000_000:
        raise ValueError("L2 requires >=100M model parameters; use smoke for tiny policies")
    model.config.use_cache = False
    action_ids = [tokenizer.encode(a, add_special_tokens=False) for a in ACTIONS]
    if any(len(ids) != 1 for ids in action_ids) or len({ids[0] for ids in action_ids}) != 4:
        raise ValueError("model tokenizer must encode A/B/C/D as distinct single tokens")
    action_ids = torch.tensor([ids[0] for ids in action_ids], device=device)

    def distribution(prompt):
        messages = [{"role": "user", "content": prompt}]
        text = (tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                if tokenizer.chat_template else prompt + "\nSvar:")
        tokens = tokenizer(text, return_tensors="pt").to(device)
        if tokens.input_ids.shape[1] > 2048:
            raise ValueError("prompt exceeds 2048-token budget")
        logits = model(**tokens).logits[0, -1, action_ids]
        if not torch.isfinite(logits).all():
            raise ValueError("non-finite logits")
        return torch.distributions.Categorical(logits=logits)

    def greedy(prompt):
        with torch.no_grad():
            return ACTIONS[int(distribution(prompt).probs.argmax())]

    model.eval()
    evaluation_seeds = list(range(10000, 10000 + eval_cases))
    before = evaluate(environment_id, greedy, evaluation_seeds)
    # A fixed held-out set is evaluated once before and once after the fixed run.
    # Never select checkpoints or tune hyperparameters on this eval split.
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    env = load(environment_id)
    curve = []
    start_weight = next(model.parameters()).detach().clone()
    for step in range(steps):
        model.train()
        optimizer.zero_grad()
        losses, rewards = [], []
        for item in range(batch_size):
            env.reset(seed * 1000000 + step * batch_size + item, "train")
            dist = distribution(env.public_prompt())
            action = dist.sample()
            reward = env.step(ACTIONS[int(action)])["reward"]
            # Fixed chance baseline. Only environment rewards drive updates.
            loss = policy_gradient_loss(dist, action, reward)
            if not torch.isfinite(loss):
                raise ValueError("non-finite loss")
            (loss / batch_size).backward()
            losses.append(float(loss.detach()))
            rewards.append(reward)
        norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0))
        if not math.isfinite(norm):
            raise ValueError("non-finite gradient norm")
        optimizer.step()
        row = {"step": step + 1, "loss": sum(losses) / batch_size,
               "reward": sum(rewards) / batch_size, "gradient_norm": norm}
        curve.append(row)
        print(row, flush=True)
    changed = not torch.equal(start_weight, next(model.parameters()).detach())
    if not changed or not any(row["gradient_norm"] > 0 for row in curve):
        raise ValueError("no effective training update detected")
    model.eval()
    after = evaluate(environment_id, greedy, evaluation_seeds)
    model.save_pretrained(output / "checkpoint", safe_serialization=True)
    tokenizer.save_pretrained(output / "checkpoint")
    checkpoint_hash = hashlib.sha256()
    for path in sorted((output / "checkpoint").rglob("*")):
        if path.is_file():
            checkpoint_hash.update(path.name.encode())
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    checkpoint_hash.update(block)
    stats = paired_bootstrap(before, after)
    improved = stats["delta"] >= .05 and stats["ci95"][0] > 0
    return save_report(output / "report.json", {
        "level": "L3" if improved else "L2", "status": "passed",
        "environment": environment_id, "L1": l1, "model": model_id, "revision": revision,
        "resolved_revision": getattr(model.config, "_commit_hash", None),
        "parameters": parameters, "algorithm": "REINFORCE, categorical A/B/C/D, baseline=0.25",
        "config": {"steps": steps, "batch_size": batch_size, "eval_cases": eval_cases,
                   "learning_rate": learning_rate, "seed": seed, "device": device,
                   "threads": threads, "max_prompt_tokens": 2048},
        "runtime": {"torch": torch.__version__, "transformers": transformers.__version__},
        "weights_changed": changed, "checkpoint_sha256": checkpoint_hash.hexdigest(),
        "training_curve": curve, "before": before, "after": after,
        "paired_improvement": stats,
        "l3_outcome": "passed" if improved else "inconclusive",
        "limitations": "Public held-out seeds; independent replication required for trusted promotion."})
