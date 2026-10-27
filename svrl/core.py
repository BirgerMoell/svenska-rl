"""A deliberately small single-turn contract; no framework dependency."""
import hashlib
import importlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIONS = ("A", "B", "C", "D")


@dataclass(frozen=True)
class Task:
    instruction: str
    choices: tuple
    answer: str

    def observation(self):
        return {"instruction": self.instruction,
                "actions": dict(zip(ACTIONS, self.choices)), "max_steps": 1}

    def prompt(self):
        lines = [self.instruction, ""]
        lines.extend(f"{key}: {value}" for key, value in zip(ACTIONS, self.choices))
        return "\n".join(lines) + "\nSvara endast med A, B, C eller D."


def task_rng(environment_id, seed, split):
    if split not in ("train", "dev", "eval"):
        raise ValueError("split must be train, dev, or eval")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    digest = hashlib.sha256(f"{environment_id}:{split}:{seed}".encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def multiple_choice(rng, instruction, correct, distractors):
    wrong = list(dict.fromkeys(str(x) for x in distractors if str(x) != str(correct)))
    if len(wrong) < 3:
        raise ValueError("three distinct distractors required")
    choices = [str(correct)] + rng.sample(wrong, 3)
    rng.shuffle(choices)
    return Task(instruction, tuple(choices), ACTIONS[choices.index(str(correct))])


class Environment:
    id = ""

    def reset(self, seed=0, split="train"):
        self._task = self.generate(task_rng(self.id, seed, split))
        self._done = False
        return self._task.observation()

    def step(self, action):
        if not hasattr(self, "_task"):
            raise RuntimeError("reset before step")
        if self._done:
            raise RuntimeError("episode already terminated")
        self._done = True
        valid = isinstance(action, str) and action.strip() in ACTIONS
        reward = float(valid and action.strip() == self._task.answer)
        return {"observation": {"message": "Klart."}, "reward": reward,
                "terminated": True, "truncated": False,
                "info": {"valid_action": valid}}

    def reference_action(self):
        """Trusted test/qualification process only. Never expose as an agent tool."""
        return self._task.answer

    def public_prompt(self):
        return self._task.prompt()


def manifests():
    result = []
    for path in sorted((ROOT / "environments").glob("*/manifest.json")):
        data = json.loads(path.read_text())
        if data["id"] != path.parent.name:
            raise ValueError(f"manifest id mismatch: {path}")
        result.append(data)
    return result


def load(environment_id):
    available = {m["id"] for m in manifests()}
    if environment_id not in available:
        raise ValueError(f"unknown environment: {environment_id}")
    env = importlib.import_module(f"environments.{environment_id}.environment").create()
    if env.id != environment_id:
        raise ValueError("environment id differs from manifest")
    return env


def source_digest():
    """Content digest of runtime, environment code and protocol, independent of git."""
    digest = hashlib.sha256()
    paths = [ROOT / "pyproject.toml", ROOT / "docs" / "validation.md"]
    for base in ("svrl", "environments", "tests"):
        paths.extend(p for p in (ROOT / base).rglob("*")
                     if p.suffix in (".py", ".json") and "__pycache__" not in p.parts)
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()
