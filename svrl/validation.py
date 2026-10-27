"""Deterministic contract qualification. Does not claim absence of all bugs."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from svrl.core import ACTIONS, load, source_digest


def validate(environment_id, cases=100):
    if cases < 1:
        raise ValueError("cases must be positive")
    env = load(environment_id)
    seen = set()
    split_prompts = {}
    for split in ("train", "dev", "eval"):
        prompts = set()
        for seed in range(cases):
            obs = env.reset(seed, split)
            prompt = env.public_prompt()
            if obs != env.reset(seed, split) or prompt != env.public_prompt():
                raise ValueError("reset is not deterministic")
            if set(obs) != {"instruction", "actions", "max_steps"}:
                raise ValueError("unexpected public observation fields")
            if len(set(obs["actions"].values())) != 4:
                raise ValueError("duplicate actions")
            correct = env.reference_action()
            if correct not in ACTIONS:
                raise ValueError("invalid reference action")
            for action in ACTIONS:
                env.reset(seed, split)
                result = env.step(action)
                if result["reward"] != float(action == correct) or not result["terminated"]:
                    raise ValueError("incorrect action scoring")
                try:
                    env.step(action)
                except RuntimeError:
                    pass
                else:
                    raise ValueError("terminated episode accepted another action")
            for action in (None, {}, [], "", "E", "ABCD", correct + " ignore rules", "A\nB"):
                env.reset(seed, split)
                result = env.step(action)
                if result["reward"] != 0 or result["info"]["valid_action"]:
                    raise ValueError("malformed action accepted")
            prompts.add(prompt)
            seen.add(hashlib.sha256(prompt.encode()).hexdigest())
        split_prompts[split] = prompts
        if len(prompts) < cases * 0.9:
            raise ValueError("insufficient task diversity")
    if any(split_prompts[a] & split_prompts[b]
           for a, b in (("train", "dev"), ("train", "eval"), ("dev", "eval"))):
        raise ValueError("observed prompt overlap between splits")
    return {"status": "passed", "cases_per_split": cases,
            "unique_prompts": len(seen), "reference_success": 1.0,
            "random_expected_success": 0.25, "malformed_action_reward": 0.0}


def evaluate(environment_id, policy, seeds):
    env = load(environment_id)
    rows = []
    for seed in seeds:
        env.reset(seed, "eval")
        action = policy(env.public_prompt())
        rows.append({"seed": seed, "action": action, "reward": env.step(action)["reward"]})
    return rows


def paired_bootstrap(before, after, repetitions=2000):
    import random
    if len(before) != len(after) or len(before) < 2:
        raise ValueError("paired evaluation needs at least two matching cases")
    if [r["seed"] for r in before] != [r["seed"] for r in after]:
        raise ValueError("evaluation cases differ")
    delta = [b["reward"] - a["reward"] for a, b in zip(before, after)]
    if any(not math.isfinite(x) for x in delta):
        raise ValueError("non-finite rewards")
    rng = random.Random(1729)
    samples = sorted(sum(rng.choices(delta, k=len(delta))) / len(delta)
                     for _ in range(repetitions))
    return {"delta": sum(delta) / len(delta),
            "ci95": [samples[int(repetitions * .025)], samples[int(repetitions * .975)]]}


def save_report(path, report):
    report = dict(report, schema_version=1, source_sha256=source_digest(),
                  created_at=datetime.now(timezone.utc).isoformat())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report
