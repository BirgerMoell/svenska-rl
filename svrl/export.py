"""Export v0.2 environments as RL training data.

Typed environments export self-contained rows: the prompt as chat messages plus `ground_truth`, a JSON answer
spec that `svrl.answers.score_answer(spec, completion)` scores without the generator. That is the shape
open-instruct/TMAX-style RLVR trainers consume (prompt + ground truth + a verifier keyed by `dataset`).
Tool environments export the episode handle (env, seed, split) with the instruction and tool schemas; a
multi-turn runtime replays the episode through `svrl.core.load(env).reset(seed, split)`.

    python3 -m svrl.cli export invoice_amount_due --split train --count 5000 --out data/invoice_amount_due-train.jsonl
    python3 -m svrl.cli export-hf --out hf/svenska-rl-kontoret --count 2000   # every v0.2 env, train/dev/eval
"""
from __future__ import annotations

import json
from pathlib import Path

from svrl.core import load, manifests, source_digest

def rows(environment_id: str, split: str, count: int, start: int = 0):
    env = load(environment_id)
    interaction = getattr(env, "interaction", "single_turn_four_actions")
    for seed in range(start, start + count):
        obs = env.reset(seed, split)
        base = {"id": f"{environment_id}-{split}-{seed}", "env": environment_id, "split": split, "seed": seed,
                "language": "sv", "interaction": interaction}
        if interaction == "typed_answer":
            yield {**base, "messages": [{"role": "user", "content": env.public_prompt()}],
                   "ground_truth": json.dumps(env._task.spec, ensure_ascii=False), "dataset": "svrl_typed",
                   "answer_type": obs["answer_type"], "meta": env._task.meta}
        elif interaction == "tool_episode":
            yield {**base, "messages": [{"role": "user", "content": obs["instruction"]}], "tools": obs["tools"],
                   "max_steps": obs["max_steps"], "ground_truth": json.dumps(env.ground_truth()),
                   "dataset": "svrl_tool_episode", "meta": env._task.meta}
        else:
            raise ValueError("v0.1 multiple-choice environments are not exported; use contract v0.2")


def export(environment_id: str, split: str, count: int, out: str, start: int = 0) -> dict:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows(environment_id, split, count, start):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return {"environment": environment_id, "split": split, "rows": n, "path": str(path)}


CARD = """---
language:
- sv
license: apache-2.0
pretty_name: Svenska RL – Kontoret
tags:
- rl-environment
- reinforcement-learning
- rlvr
- swedish
- office
- tool-use
configs:
{configs}
---

# Svenska RL – Kontoret

Swedish office-work RL environments from [svenska-rl](https://github.com/BirgerMoell/svenska-rl) (contract v0.2):
synthetic tasks from one simulated Swedish organisation, scored by code against simulator state.

- **Typed tasks** (`svrl_typed`): one prompt, a free-form completion ending in `SVAR: …`; `ground_truth` is a
  JSON answer spec scored by `svrl.answers.score_answer(spec, completion)`.
- **Tool episodes** (`svrl_tool_episode`): multi-turn tool use; `ground_truth` is the episode handle and the
  episode runs through `svrl.core.load(env).reset(seed, split)` (`svrl.rollout` is a reference runner).

| Environment | Interaction | Description |
|---|---|---|
{table}

Splits use separate SHA-256 RNG namespaces; eval is public and reproducible, not a secret benchmark.
All data is synthetic (no real persons or companies). Source digest: `{digest}`.
"""


def export_hf(out: str, count: int, eval_count: int | None = None) -> dict:
    root = Path(out)
    configs, table, report = [], [], {}
    for m in manifests():
        if m.get("contract") != "0.2":
            continue
        eid = m["id"]
        files = []
        for split, n in (("train", count), ("dev", eval_count or max(64, count // 10)),
                         ("eval", eval_count or max(64, count // 10))):
            target = root / "data" / eid / f"{split}.jsonl"
            report[f"{eid}/{split}"] = export(eid, split, n, str(target))["rows"]
            files.append(f"    - split: {'validation' if split == 'dev' else 'test' if split == 'eval' else split}\n"
                         f"      path: data/{eid}/{split}.jsonl")
        configs.append(f"- config_name: {eid}\n  data_files:\n" + "\n".join(files))
        table.append(f"| `{eid}` | {m['interaction']} | {m['title']}: {m.get('description', '')} |")
    (root / "README.md").write_text(CARD.format(configs="\n".join(configs), table="\n".join(table),
                                                digest=source_digest()), encoding="utf-8")
    return {"path": str(root), "rows": report}
