"""Contract qualification and paired evaluation statistics. Finite tests cannot prove that an
environment has no bugs."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from svrl.core import load, source_digest


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


# --- contract qualification ----------------------------------------------------------------------------------------------

PROBE_MAX_MEAN = 0.3      # a shortcut strategy may not earn more than this mean reward
ABSTAIN_RANGE = (0.03, 0.3)


def _numbers(prompt):
    import re
    return re.findall(r"\d[\d  ]*(?:,\d{2})?", prompt)


def typed_probes(env, prompt):
    """Shortcut completions that must not pay off: empty, format-only, abstain-always, copy numbers from the
    prompt, list every candidate, and type-specific trivial answers."""
    import re
    from svrl import answers
    nums = [n.strip() for n in _numbers(prompt)]
    amounts = re.findall(r"\d[\d  ]*,\d{2} kr", prompt)
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", prompt)
    probes = {"empty": "", "no_answer_line": "Jag har räknat på det.", "bare_svar": "SVAR:",
              "abstain": f"SVAR: {answers.ABSTAIN}",
              "first_number": f"SVAR: {nums[0]}" if nums else "SVAR: 0",
              "last_amount": f"SVAR: {amounts[-1]}" if amounts else "SVAR: 0 kr",
              "largest_amount": "SVAR: " + max(amounts, key=lambda a: _amount(a)) if amounts else "SVAR: 0 kr",
              "all_numbers": "SVAR: " + " ".join(nums[:40]),
              "first_date": f"SVAR: {dates[0]} 08:00" if dates else "SVAR: 2026-01-01 08:00",
              "json_empty_object": "SVAR: {}", "json_empty_list": "SVAR: []",
              "think_only": "<think>SVAR: 1 kr</think>"}
    if env._task.answer_type == "mapping":
        keys = list(env._task.spec.get("value", {}))
        probes["all_unmatched"] = "SVAR: " + json.dumps({k: "omatchad" for k in keys})
        probes["all_zero"] = "SVAR: " + json.dumps({k: 0 for k in keys})
        probes["decline"] = "SVAR: " + json.dumps({"leverantor": "avstå"})
    if env._task.answer_type == "strings":
        probes["all_numbers_json"] = "SVAR: " + json.dumps(nums, ensure_ascii=False)
    return probes


def _amount(text):
    from svrl.kontoret import fmt
    return fmt.parse_money(text) or 0


def validate_typed(environment_id, cases=100):
    from svrl import answers
    env = load(environment_id)
    split_prompts, probe_rewards, abstain_tasks = {}, {}, 0
    for split in ("train", "dev", "eval"):
        prompts = set()
        for seed in range(cases):
            obs = env.reset(seed, split)
            prompt, spec = env.public_prompt(), json.dumps(env._task.spec, sort_keys=True)
            if obs != env.reset(seed, split) or prompt != env.public_prompt() or \
                    spec != json.dumps(env._task.spec, sort_keys=True):
                raise ValueError("reset is not deterministic")
            if set(obs) != {"instruction", "answer_type", "max_steps"}:
                raise ValueError("unexpected public observation fields")
            ref = env.reference_completion()
            for completion in (ref, "Låt mig räkna.\n\n" + ref, "<think>utkast\nSVAR: fel</think>\n" + ref):
                env.reset(seed, split)
                if env.step(completion)["reward"] != 1.0:
                    raise ValueError(f"reference completion not rewarded (seed {seed}, {split}): {completion[-200:]}")
                try:
                    env.step(completion)
                except RuntimeError:
                    pass
                else:
                    raise ValueError("terminated episode accepted another completion")
            abstain_tasks += env._task.spec["type"] == "abstain"
            for name, completion in typed_probes(env, prompt).items():
                if completion == ref:
                    continue
                env.reset(seed, split)
                probe_rewards.setdefault(name, []).append(env.step(completion)["reward"])
            for bad in (None, 42, {}, ["SVAR: 1"]):
                env.reset(seed, split)
                if env.step(bad)["reward"] != 0:
                    raise ValueError("non-text completion rewarded")
            prompts.add(prompt)
        if len(prompts) < cases * 0.9:
            raise ValueError("insufficient task diversity")
        split_prompts[split] = prompts
    if any(split_prompts[a] & split_prompts[b] for a, b in (("train", "dev"), ("train", "eval"), ("dev", "eval"))):
        raise ValueError("observed prompt overlap between splits")
    probe_means = {k: sum(v) / len(v) for k, v in probe_rewards.items()}
    exploitable = {k: round(v, 3) for k, v in probe_means.items() if v > PROBE_MAX_MEAN}
    if exploitable:
        raise ValueError(f"shortcut probes earn too much reward: {exploitable}")
    abstain_rate = abstain_tasks / (3 * cases)
    if env.abstention and not ABSTAIN_RANGE[0] <= abstain_rate <= ABSTAIN_RANGE[1]:
        raise ValueError(f"abstention share {abstain_rate:.2f} outside {ABSTAIN_RANGE}")
    if not env.abstention and abstain_tasks:
        raise ValueError("unanswerable tasks in an environment that does not declare abstention")
    return {"status": "passed", "contract": "0.2", "interaction": "typed_answer", "cases_per_split": cases,
            "unique_prompts": sum(len(p) for p in split_prompts.values()), "reference_success": 1.0,
            "abstain_share": round(abstain_rate, 3),
            "probe_mean_reward": {k: round(v, 3) for k, v in sorted(probe_means.items())}}


def validate_tools(environment_id, cases=50):
    from svrl.contract import run_actions
    env = load(environment_id)
    split_prompts, probe_rewards = {}, {}
    for split in ("train", "dev", "eval"):
        prompts = set()
        for seed in range(cases):
            obs = env.reset(seed, split)
            if obs != env.reset(seed, split):
                raise ValueError("reset is not deterministic")
            if set(obs) != {"instruction", "tools", "max_steps"}:
                raise ValueError("unexpected public observation fields")
            names = {t["function"]["name"] for t in obs["tools"]}
            result = run_actions(env, env.reference_actions())
            if result["reward"] != 1.0 or not result["terminated"]:
                raise ValueError(f"reference solution not rewarded (seed {seed}, {split}): {result['info']}")
            try:
                env.step({"final": "igen"})
            except RuntimeError:
                pass
            else:
                raise ValueError("terminated episode accepted another action")
            env.reset(seed, split)
            probe_rewards.setdefault("finish_immediately", []).append(env.step({"final": "Klart."})["reward"])
            env.reset(seed, split)
            for bad in ({"tool": "finns_inte", "arguments": {}}, {"tool": sorted(names)[0], "arguments": "x"},
                        {"tool": sorted(names)[0], "arguments": {"okant": 1}}, 17, {"x": 1},
                        "<tool_call>{inte json</tool_call>"):
                step = env.step(bad)
                if step["terminated"] or "error" not in step["observation"]:
                    raise ValueError(f"malformed action not reported as an error: {bad!r}")
            # Read-only spam until the step limit: must truncate, and must not earn reward by itself.
            env.reset(seed, split)
            reader = next(t for t in env._task.tools if not t.mutates and not t.parameters.get("required"))
            step = {"terminated": False, "truncated": False}
            for _ in range(env._task.max_steps + 1):
                step = env.step({"tool": reader.name, "arguments": {}})
                if step["terminated"] or step["truncated"]:
                    break
            if not step["truncated"]:
                raise ValueError("step limit not enforced")
            probe_rewards.setdefault("read_until_limit", []).append(step["reward"])
            # Reference without its last mutating step(s): must not earn full reward.
            ref = env.reference_actions()
            mutating = [i for i, a in enumerate(ref) if "tool" in a and env._tools[a["tool"]].mutates]
            if mutating:
                env.reset(seed, split)
                partial = run_actions(env, [a for i, a in enumerate(ref) if i != mutating[0]])
                if partial["reward"] >= 1.0:
                    raise ValueError("dropping a required state change still earns full reward")
            # Tool tasks vary in the system state more than in the instruction: fingerprint both.
            prompts.add(hashlib.sha256((obs["instruction"] + json.dumps(ref, sort_keys=True, ensure_ascii=False)
                                        ).encode()).hexdigest())
        if len(prompts) < cases * 0.9:
            raise ValueError("insufficient task diversity")
        split_prompts[split] = prompts
    if any(split_prompts[a] & split_prompts[b] for a, b in (("train", "dev"), ("train", "eval"), ("dev", "eval"))):
        raise ValueError("observed task overlap between splits")
    probe_means = {k: sum(v) / len(v) for k, v in probe_rewards.items()}
    exploitable = {k: round(v, 3) for k, v in probe_means.items() if v > PROBE_MAX_MEAN}
    if exploitable:
        raise ValueError(f"shortcut probes earn too much reward: {exploitable}")
    return {"status": "passed", "contract": "0.2", "interaction": "tool_episode", "cases_per_split": cases,
            "reference_success": 1.0, "probe_mean_reward": {k: round(v, 3) for k, v in sorted(probe_means.items())}}


def qualify(environment_id, cases=None):
    """Contract qualification for an environment (typed answer or tool episode)."""
    env = load(environment_id)
    if env.interaction == "typed_answer":
        return validate_typed(environment_id, cases or 100)
    if env.interaction == "tool_episode":
        return validate_tools(environment_id, cases or 50)
    raise ValueError(f"unknown interaction: {env.interaction}")
