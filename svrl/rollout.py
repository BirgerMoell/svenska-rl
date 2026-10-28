"""Reference rollout runner: evaluate any OpenAI-compatible chat model (vLLM, Ollama, llama.cpp, a hosted API)
on v0.2 environments. Standard library only.

    python3 -m svrl.cli rollout invoice_amount_due --base-url http://127.0.0.1:11434/v1 --model agora \
        --split eval --count 64 --out runs/agora-invoice_amount_due.jsonl

Typed tasks: one chat completion, scored with the environment. Tool episodes: the tool schemas are passed as
`tools`; the model's `tool_calls` (or Hermes `<tool_call>` text) are executed in the environment and the results
returned as `tool` messages until the model answers without a tool call or the step limit is reached.
Greedy decoding by default so before/after comparisons are paired.
"""
from __future__ import annotations

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from svrl.contract import parse_assistant
from svrl.core import load


class ChatClient:
    def __init__(self, base_url: str, model: str, api_key: str = "EMPTY", temperature: float = 0.0,
                 max_tokens: int = 2048, timeout: int = 600, extra: dict | None = None):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model, self.api_key, self.timeout = model, api_key, timeout
        self.params = {"temperature": temperature, "max_tokens": max_tokens, **(extra or {})}

    def chat(self, messages: list, tools: list | None = None) -> dict:
        body = {"model": self.model, "messages": messages, **self.params}
        if tools:
            body["tools"] = tools
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read())["choices"][0]["message"]
            except (OSError, KeyError, json.JSONDecodeError):
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)


def run_typed(env, client: ChatClient, seed: int, split: str) -> dict:
    env.reset(seed, split)
    message = client.chat([{"role": "user", "content": env.public_prompt()}])
    completion = message.get("content") or ""
    result = env.step(completion)
    return {"reward": result["reward"], "info": result["info"], "completion": completion}


def _actions(message: dict) -> list:
    calls = message.get("tool_calls") or []
    actions = []
    for call in calls:
        fn = call.get("function", {})
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except json.JSONDecodeError:
                args = None
        actions.append({"tool": fn.get("name"), "arguments": args, "id": call.get("id")})
    return actions or parse_assistant(message.get("content") or "")


def run_tools(env, client: ChatClient, seed: int, split: str) -> dict:
    obs = env.reset(seed, split)
    messages = [{"role": "user", "content": obs["instruction"]}]
    result, transcript = None, []
    while result is None or not (result["terminated"] or result["truncated"]):
        message = client.chat(messages, tools=obs["tools"])
        actions = _actions(message)
        assistant = {"role": "assistant", "content": message.get("content") or ""}
        tool_actions = [a for a in actions if "tool" in a]
        if tool_actions:
            assistant["tool_calls"] = [{"id": a.get("id") or f"call_{len(transcript)}_{i}", "type": "function",
                                        "function": {"name": a["tool"] or "", "arguments": json.dumps(a["arguments"])}}
                                       for i, a in enumerate(tool_actions)]
        messages.append(assistant)
        for i, action in enumerate(actions):
            step_action = {k: v for k, v in action.items() if k != "id"}
            result = env.step(step_action)
            transcript.append({"action": step_action, "observation": result["observation"]})
            if "tool" in action:
                messages.append({"role": "tool", "tool_call_id": assistant["tool_calls"][i]["id"],
                                 "content": json.dumps(result["observation"], ensure_ascii=False)})
            if result["terminated"] or result["truncated"]:
                break
    return {"reward": result["reward"], "info": result["info"], "transcript": transcript}


def rollout(environment_id: str, client: ChatClient, split: str = "eval", count: int = 64, start: int = 0,
            workers: int = 4, out: str | None = None) -> dict:
    env_type = load(environment_id).interaction

    def one(seed):
        env = load(environment_id)  # one environment instance per episode (thread safety)
        try:
            row = (run_typed if env_type == "typed_answer" else run_tools)(env, client, seed, split)
        except Exception as error:  # a failed request is reported, never silently scored
            row = {"reward": None, "error": f"{type(error).__name__}: {error}"}
        return {"env": environment_id, "split": split, "seed": seed, **row}

    seeds = list(range(start, start + count))
    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(one, seeds))
    if out:
        with open(out, "w", encoding="utf-8") as f:
            for row in results:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    scored = [r for r in results if r["reward"] is not None]
    by_level = {}
    for r in scored:
        level = str(r["info"].get("meta", {}).get("level", "-"))
        by_level.setdefault(level, []).append(r["reward"])
    return {"environment": environment_id, "model": client.model, "split": split, "episodes": len(results),
            "errors": len(results) - len(scored),
            "mean_reward": round(sum(r["reward"] for r in scored) / max(1, len(scored)), 4),
            "solved": round(sum(r["reward"] >= 1.0 for r in scored) / max(1, len(scored)), 4),
            "by_level": {k: round(sum(v) / len(v), 3) for k, v in sorted(by_level.items())}}
