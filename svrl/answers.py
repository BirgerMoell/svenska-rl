"""Answer extraction and typed scoring for typed-answer environments (free-form answers, no multiple choice).

Every typed task asks for a final line `SVAR: <answer>`; JSON answers may span several lines after `SVAR:`.
Reasoning before the line is allowed and ignored; a `<think>...</think>` trace is stripped. Only the LAST `SVAR:`
counts, and an answer that hedges (several amounts, several dates) does not parse, so listing every candidate
never earns reward. `INFORMATION SAKNAS` is the abstention answer: correct exactly when the task is unanswerable.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter

from svrl.kontoret import fmt

ABSTAIN = "INFORMATION SAKNAS"
MAX_ANSWER_CHARS = 4000


def strip_reasoning(text: str) -> str:
    text = text or ""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text


def final_answer(text: str) -> str | None:
    """Text after the last `SVAR:` (case-insensitive), or None."""
    body = strip_reasoning(text)
    matches = list(re.finditer(r"(?im)^\s*\**\s*svar\s*\**\s*:\s*", body))
    if not matches:
        return None
    answer = body[matches[-1].end():].strip()
    answer = re.sub(r"^\*+\s*|\s*\*+$", "", answer)  # markdown bold around the answer: **SVAR:** 12 kr**
    answer = re.sub(r"^```(?:json)?\s*|\s*```$", "", answer).strip()
    if not answer or len(answer) > MAX_ANSWER_CHARS:
        return None
    return answer


def is_abstention(answer: str | None) -> bool:
    return answer is not None and norm(answer).strip(" .!") == norm(ABSTAIN)


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"\s+", " ", text).strip()


def key_norm(key) -> str:
    """JSON keys compare without case, surrounding space or diacritics ("leverantör" == "leverantor")."""
    text = unicodedata.normalize("NFKD", str(key).strip().casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def first_line(answer: str) -> str:
    return answer.splitlines()[0].strip() if answer else ""


def parse_json(answer: str):
    if answer is None:
        return None
    start = min([i for i in (answer.find("{"), answer.find("[")) if i >= 0], default=-1)
    if start < 0:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(answer[start:])
        return value
    except json.JSONDecodeError:
        return None


# --- answer specs -------------------------------------------------------------------------------------------
# A spec is a JSON-serialisable dict, so exported ground truth can be scored without the generator:
#   {"type": "money", "value": <öre>}            exact amount
#   {"type": "date", "value": "YYYY-MM-DD"}
#   {"type": "datetime", "date": "YYYY-MM-DD", "time": "HH:MM"}
#   {"type": "integer", "value": int}            exactly one integer in the answer line (units allowed: "40 st")
#   {"type": "text", "value": str, "aliases": [...]}   normalised exact match
#   {"type": "abstain"}                          the task is unanswerable; only INFORMATION SAKNAS scores
#   {"type": "mapping", "value": {key: value}, "partial": true}   JSON object; per-key credit. A value
#       {"money": öre} matches any single amount equal to it ("1 234,50 kr", "1234.50"); null means the key
#       must be absent or null
#   {"type": "strings", "value": [str, ...]}                     JSON list of exact strings; multiset F1
# Partial credit is reported as `score` (0..1); `reward` is 1.0 only for a fully correct answer unless the
# environment opts into partial reward. Abstaining on an answerable task always scores 0.

def score_answer(spec: dict, text: str) -> dict:
    answer = final_answer(text)
    if answer is None:
        return {"reward": 0.0, "score": 0.0, "parsed": None, "reason": "no SVAR line"}
    if spec["type"] == "abstain":
        ok = is_abstention(answer)
        return {"reward": float(ok), "score": float(ok), "parsed": answer[:200], "reason": "abstain"}
    if is_abstention(answer):
        return {"reward": 0.0, "score": 0.0, "parsed": ABSTAIN, "reason": "abstained on answerable task"}
    kind = spec["type"]
    if kind == "money":
        value = fmt.parse_money(first_line(answer))
        ok = value == spec["value"]
        return {"reward": float(ok), "score": float(ok), "parsed": value, "reason": kind}
    if kind == "date":
        value = fmt.parse_date(first_line(answer))
        ok = value is not None and value.isoformat() == spec["value"]
        return {"reward": float(ok), "score": float(ok), "parsed": value and value.isoformat(), "reason": kind}
    if kind == "datetime":
        line = first_line(answer)
        d, t = fmt.parse_date(line), fmt.parse_time(re.sub(r"\d{4}-\d{2}-\d{2}", " ", line))
        ok = d is not None and d.isoformat() == spec["date"] and t == spec["time"]
        return {"reward": float(ok), "score": float(ok), "parsed": [d and d.isoformat(), t], "reason": kind}
    if kind == "integer":
        found = re.findall(r"-?\d[\d \u00a0]*", first_line(answer))
        value = int(re.sub(r"[ \u00a0]", "", found[0])) if len(found) == 1 else None
        ok = value == spec["value"]
        return {"reward": float(ok), "score": float(ok), "parsed": value, "reason": kind}
    if kind == "text":
        targets = {norm(spec["value"]), *(norm(a) for a in spec.get("aliases", []))}
        ok = norm(first_line(answer)).strip(" .") in targets
        return {"reward": float(ok), "score": float(ok), "parsed": first_line(answer)[:200], "reason": kind}
    if kind == "mapping":
        value = parse_json(answer)
        if not isinstance(value, dict):
            return {"reward": 0.0, "score": 0.0, "parsed": None, "reason": "no JSON object"}
        expected = {key_norm(k): v for k, v in spec["value"].items()}
        got = {key_norm(k): v for k, v in value.items()}
        hits = sum(_value_matches(v, got.get(k)) for k, v in expected.items())
        extra = len([k for k in got if k not in expected and got[k] is not None])
        score = max(0.0, (hits - extra) / len(expected))
        exact = hits == len(expected) and not extra
        return {"reward": 1.0 if exact else (score if spec.get("partial") else 0.0), "score": score,
                "parsed": value, "reason": kind}
    if kind == "strings":
        value = parse_json(answer)
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            return {"reward": 0.0, "score": 0.0, "parsed": None, "reason": "no JSON list of strings"}
        got, expected = Counter(x.strip() for x in value), Counter(spec["value"])
        tp = sum((got & expected).values())
        total = sum(got.values()) + sum(expected.values())
        f1 = 2 * tp / total if total else 1.0
        exact = got == expected
        return {"reward": 1.0 if exact else (f1 if spec.get("partial") else 0.0), "score": f1,
                "parsed": value[:50], "reason": kind}
    raise ValueError(f"unknown answer type: {kind}")


def _value_matches(expected, got) -> bool:
    if expected is None:
        return got is None
    if isinstance(expected, dict) and "money" in expected:
        return got is not None and fmt.parse_money(str(got)) == expected["money"]
    return got is not None and norm(str(got)) == norm(str(expected))


def _render_value(value):
    if isinstance(value, dict) and "money" in value:
        return fmt.money(value["money"])
    return value


def render_reference(spec: dict) -> str:
    """A canonical correct completion for a spec (used by qualification, never shown to agents)."""
    kind = spec["type"]
    if kind == "abstain":
        return f"SVAR: {ABSTAIN}"
    if kind == "money":
        return f"SVAR: {fmt.money(spec['value'])}"
    if kind == "date":
        return f"SVAR: {spec['value']}"
    if kind == "datetime":
        return f"SVAR: {spec['date']} {spec['time']}"
    if kind == "text":
        return f"SVAR: {spec['value']}"
    if kind == "integer":
        return f"SVAR: {spec['value']}"
    if kind == "mapping":
        return "SVAR: " + json.dumps({k: _render_value(v) for k, v in spec["value"].items()}, ensure_ascii=False)
    if kind == "strings":
        return "SVAR: " + json.dumps(spec["value"], ensure_ascii=False)
    raise ValueError(kind)
