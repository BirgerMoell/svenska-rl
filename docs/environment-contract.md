# Environment contract v0.2

Office work produces amounts, dates, filled-in records, lists and changed system state, so the model produces
the answer itself; there are no multiple-choice tasks (v0.1, four options A–D, was retired in v0.2: guessing
scored 25 % and distractors could be eliminated without doing the work).

Two interaction types. Both use SHA-256 seeded `reset(seed, split)` with separate train/dev/eval namespaces,
ground truth from simulator state (never from a model judging itself), all business rules stated in the task,
and synthetic data only. Each package exports `create()` from `environment.py` plus a `manifest.json` whose id
matches the directory; `svrl.core.load(id)` discovers it.

## 1. Typed answer (`interaction: typed_answer`)

Subclass `svrl.contract.TypedEnvironment` and implement `generate(rng) -> TypedTask(instruction, spec,
answer_type, meta)`.

- The model writes free text and ends with `SVAR: <answer>`. Reasoning before it is fine; a `<think>` trace is
  ignored; only the last `SVAR:` counts.
- `spec` is a JSON answer spec scored by `svrl.answers.score_answer`:

| type | answer | scoring |
|---|---|---|
| `money` | one amount, e.g. `1 234,50 kr` (tolerant: `1234.50`, `1 234:50 SEK`) | exact öre |
| `date` / `datetime` | `ÅÅÅÅ-MM-DD` / `ÅÅÅÅ-MM-DD TT:MM` | exact |
| `text` | one line | normalised exact match, optional aliases |
| `mapping` | JSON object | per key; extra keys cost credit |
| `strings` | JSON list of exact strings | multiset F1 |
| `abstain` | `INFORMATION SAKNAS` | the task is unanswerable |

- An answer that hedges (two amounts, two dates) does not parse. Listing candidates never pays.
- `reward` is 1.0 only for a fully correct answer, unless the environment sets `partial_reward = True`; then
  mapping/strings tasks give their partial score. Abstaining on an answerable task scores 0.
- Set `abstention = True` if some tasks are unanswerable (3–30 % of tasks). The prompt then always carries the
  abstention hint, so its presence reveals nothing.
- The format hint must not leak the answer type of a special case (e.g. `meeting_slot` asks for a date and time
  even when the answer is `INGEN TID`).

Public observation: `instruction`, `answer_type`, `max_steps` (= 1).

## 2. Tool episode (`interaction: tool_episode`)

Subclass `svrl.contract.ToolEnvironment` and implement `generate(rng) -> ToolTask(instruction, state, tools,
check, reference, max_steps, meta)`.

- `tools` are `svrl.contract.Tool(name, description, parameters (JSON schema), fn, mutates)`. `fn(state, **args)`
  reads or changes the simulated systems; raise `ToolError` for business errors (returned to the model as
  `{"error": ...}`). Arguments are checked against the schema before the call.
- An action is `{"tool": name, "arguments": {...}}` or `{"final": text}`; a string is parsed as Hermes/Qwen
  `<tool_call>{...}</tool_call>` blocks, otherwise as the final message.
- The episode ends with a final message (terminated) or at `max_steps` (truncated); either way `check(state,
  final)` scores the END STATE. Penalise wrong side effects (a wrong registration, an e-mail to the wrong person),
  so that doing more is not free.
- `reference` is a trusted action list that reaches reward 1.0. It is used for qualification only.

Public observation: `instruction`, `tools` (OpenAI function schemas), `max_steps`.

## Qualification

`python3 -m svrl.cli check ENV_ID` runs `svrl.validation.qualify`:

- determinism of prompts and answer specs; ≥ 90 % unique tasks per split; no task shared between splits;
- the reference answer (also after reasoning text and after a `<think>` block) earns 1.0 for every seed;
- **shortcut probes** must earn ≤ 0.3 mean reward: empty answer, no `SVAR:` line, always abstaining, copying the
  first/last/largest number from the prompt, listing all numbers, empty JSON, and for tool episodes finishing
  immediately or only reading until the step limit;
- tool episodes: malformed actions return errors without ending the episode; the step limit is enforced;
  dropping a required state change costs reward.

Also write independent domain tests that re-solve tasks from the public prompt, not from the generator's
stored answer (see `tests/test_contract_v02.py`).

## Training and evaluation

- `python3 -m svrl.cli export ENV --split train --count N --out file.jsonl`: rows with chat `messages` and
  `ground_truth` (the answer spec), the shape RLVR trainers such as open-instruct consume; score with
  `svrl.answers.score_answer(json.loads(ground_truth), completion)`.
- `python3 -m svrl.cli export-hf --out DIR`: all environments as a Hugging Face dataset tagged
  `rl-environment`.
- `python3 -m svrl.cli rollout ENV --base-url URL --model NAME`: baseline any OpenAI-compatible model (vLLM,
  Ollama, llama.cpp); greedy by default for paired before/after comparisons (L3 in `docs/validation.md`).

## Translation

Keep text in the generator's templates and formatting in `svrl.kontoret.fmt` (locale table). A translation adds
templates and a locale; verifiers compare values (öre, ISO dates, JSON), not Swedish wording.
