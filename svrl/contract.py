"""Contract v0.2: typed free-form answers and multi-turn tool episodes (see docs/environment-contract-v0.2.md).

TypedEnvironment  one prompt, one free-form completion ending in `SVAR: ...`, scored by an answer spec.
ToolEnvironment   the model calls tools that read and change a simulated office system over several turns; the
                  episode ends with a final message (or the step limit) and is scored on the resulting STATE.

Both reuse the v0.1 seeding (`task_rng`: SHA-256 namespaces per environment and split) and the rule that ground
truth comes from simulator state, never from a model.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from svrl import answers
from svrl.core import task_rng

FORMAT_HINTS = {
    "money": "Avsluta med en rad i formen `SVAR: <belopp i kronor>`, till exempel `SVAR: 1 234,50 kr`.",
    "date": "Avsluta med en rad i formen `SVAR: ÅÅÅÅ-MM-DD`.",
    "datetime": "Avsluta med en rad i formen `SVAR: ÅÅÅÅ-MM-DD TT:MM`.",
    "text": "Avsluta med en rad i formen `SVAR: <svar>`.",
    "mapping": "Avsluta med `SVAR:` följt av ett JSON-objekt.",
    "strings": "Avsluta med `SVAR:` följt av en JSON-lista med strängar, exakt som de står i texten och i den ordning de förekommer.",
}
ABSTAIN_HINT = f"Om uppgiften inte går att lösa med den information som finns, svara `SVAR: {answers.ABSTAIN}`."


@dataclass
class TypedTask:
    instruction: str
    spec: dict           # answer spec (svrl.answers); `type` may be "abstain" for unanswerable variants
    answer_type: str     # the type the prompt asks for (also for abstain variants, so prompts look alike)
    meta: dict = field(default_factory=dict)  # level, family, ...: reported, never shown


class TypedEnvironment:
    id = ""
    contract = "0.2"
    interaction = "typed_answer"
    abstention = False   # whether some tasks are unanswerable (then the prompt always carries ABSTAIN_HINT)
    partial_reward = False

    def generate(self, rng) -> TypedTask:
        raise NotImplementedError

    def reset(self, seed: int = 0, split: str = "train") -> dict:
        self._seed, self._split = seed, split
        self._task = self.generate(task_rng(self.id, seed, split))
        if self.partial_reward:
            self._task.spec = {**self._task.spec, "partial": True}
        self._done = False
        return self.observation()

    def observation(self) -> dict:
        return {"instruction": self.public_prompt(), "answer_type": self._task.answer_type, "max_steps": 1}

    def public_prompt(self) -> str:
        hint = FORMAT_HINTS[self._task.answer_type]
        if self.abstention:
            hint += " " + ABSTAIN_HINT
        return f"{self._task.instruction.rstrip()}\n\n{hint}"

    def step(self, completion: Any) -> dict:
        if not hasattr(self, "_task"):
            raise RuntimeError("reset before step")
        if self._done:
            raise RuntimeError("episode already terminated")
        self._done = True
        result = answers.score_answer(self._task.spec, completion if isinstance(completion, str) else "")
        return {"observation": {"message": "Klart."}, "reward": result["reward"], "terminated": True,
                "truncated": False, "info": {**result, "meta": self._task.meta}}

    # Trusted qualification / export helpers: never expose these to an agent.
    def reference_completion(self) -> str:
        return answers.render_reference(self._task.spec)

    def ground_truth(self) -> dict:
        return {"env": self.id, "seed": self._seed, "split": self._split, "spec": self._task.spec}


# --- tool episodes --------------------------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict     # JSON schema (object)
    fn: Callable         # fn(state, **arguments) -> JSON-serialisable result
    mutates: bool = False

    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description,
                                                 "parameters": self.parameters}}


@dataclass
class ToolTask:
    instruction: str
    state: Any                          # the simulated systems; deep-copied per episode
    tools: list                         # [Tool]
    check: Callable                     # check(state, final_message) -> {"reward": float, "score": float, ...}
    reference: list                     # trusted solution: [{"tool": name, "arguments": {...}}, ..., {"final": text}]
    max_steps: int = 20
    meta: dict = field(default_factory=dict)


class ToolError(Exception):
    """Raised by a tool for a business-level error; returned to the agent as an error observation."""


def _check_arguments(tool: Tool, arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return "argumenten måste vara ett JSON-objekt"
    props = tool.parameters.get("properties", {})
    for key in tool.parameters.get("required", []):
        if key not in arguments:
            return f"argument saknas: {key}"
    for key, value in arguments.items():
        if key not in props:
            return f"okänt argument: {key}"
        expected = props[key].get("type")
        types = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
        if expected in types and (not isinstance(value, types[expected]) or
                                  (expected in ("integer", "number") and isinstance(value, bool))):
            return f"fel typ för {key}: {expected} förväntas"
        if "enum" in props[key] and value not in props[key]["enum"]:
            return f"ogiltigt värde för {key}"
    return None


_TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)


def parse_assistant(text: str) -> list:
    """Actions in an assistant message: Hermes/Qwen `<tool_call>{...}</tool_call>` blocks, else one final answer."""
    body = answers.strip_reasoning(text or "")
    calls = []
    for raw in _TOOL_CALL.findall(body):
        try:
            obj = json.loads(raw)
            calls.append({"tool": obj.get("name"), "arguments": obj.get("arguments", {})})
        except (json.JSONDecodeError, AttributeError):
            calls.append({"tool": None, "arguments": None, "malformed": raw[:200]})
    return calls or [{"final": body.strip()}]


class ToolEnvironment:
    id = ""
    contract = "0.2"
    interaction = "tool_episode"

    def generate(self, rng) -> ToolTask:
        raise NotImplementedError

    def reset(self, seed: int = 0, split: str = "train") -> dict:
        self._seed, self._split = seed, split
        self._task = self.generate(task_rng(self.id, seed, split))
        self._state = copy.deepcopy(self._task.state)
        self._tools = {t.name: t for t in self._task.tools}
        self._steps, self._done, self.trace = 0, False, []
        return self.observation()

    def observation(self) -> dict:
        return {"instruction": self._task.instruction, "tools": [t.schema() for t in self._task.tools],
                "max_steps": self._task.max_steps}

    def public_prompt(self) -> str:
        return self._task.instruction

    def step(self, action: Any) -> dict:
        if not hasattr(self, "_task"):
            raise RuntimeError("reset before step")
        if self._done:
            raise RuntimeError("episode already terminated")
        if isinstance(action, str):
            parsed = parse_assistant(action)
            if len(parsed) != 1:
                raise ValueError("one action per step; split multi-call messages with parse_assistant()")
            action = parsed[0]
        self._steps += 1
        if not isinstance(action, dict) or ("final" not in action and "tool" not in action):
            observation = {"error": "ogiltig handling: anropa ett verktyg eller skriv ett slutsvar"}
            self.trace.append({"action": repr(action)[:200], "observation": observation})
            return self._maybe_truncate(observation)
        if "final" in action:
            return self._finish(str(action["final"]), truncated=False)
        tool = self._tools.get(action.get("tool"))
        if tool is None:
            observation = {"error": f"okänt verktyg: {action.get('tool')}"}
        else:
            problem = _check_arguments(tool, action.get("arguments"))
            if problem:
                observation = {"error": problem}
            else:
                try:
                    observation = {"result": tool.fn(self._state, **action["arguments"])}
                except ToolError as error:
                    observation = {"error": str(error)}
        self.trace.append({"action": action, "observation": observation})
        return self._maybe_truncate(observation)

    def _maybe_truncate(self, observation: dict) -> dict:
        if self._steps >= self._task.max_steps:
            return self._finish("", truncated=True, observation=observation)
        return {"observation": observation, "reward": 0.0, "terminated": False, "truncated": False, "info": {}}

    def _finish(self, final: str, truncated: bool, observation: dict | None = None) -> dict:
        self._done = True
        result = self._task.check(self._state, final)
        return {"observation": observation or {"message": "Klart."}, "reward": float(result["reward"]),
                "terminated": not truncated, "truncated": truncated,
                "info": {**result, "steps": self._steps, "meta": self._task.meta}}

    # Trusted helpers.
    def reference_actions(self) -> list:
        return copy.deepcopy(self._task.reference)

    def ground_truth(self) -> dict:
        return {"env": self.id, "seed": self._seed, "split": self._split}


def run_actions(env: ToolEnvironment, actions: list) -> dict:
    """Play a scripted action list (reference or probe) and return the terminal step result."""
    result = None
    for action in actions:
        result = env.step(action)
        if result["terminated"] or result["truncated"]:
            return result
    return env.step({"final": ""}) if result is None or not (result["terminated"] or result["truncated"]) else result
