"""Environment discovery, seeding and source digests shared by all environments."""
import hashlib
import importlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def task_rng(environment_id, seed, split):
    if split not in ("train", "dev", "eval"):
        raise ValueError("split must be train, dev, or eval")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    digest = hashlib.sha256(f"{environment_id}:{split}:{seed}".encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


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
