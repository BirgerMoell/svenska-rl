"""Contract qualification of every environment plus independent domain checks that re-solve tasks
from the public prompt (not from the generator's stored answer)."""
import datetime as dt
import json
import re
import unittest

from svrl import answers
from svrl.contract import parse_assistant, run_actions
from svrl.core import load, manifests
from svrl.kontoret import fmt, ids, kalender
from svrl.validation import qualify

V02 = [m["id"] for m in manifests()]


def money_cells(row):
    return [fmt.parse_money(c) for c in re.findall(r"\d[\d  ]*,\d{2} kr", row)]


class QualificationTests(unittest.TestCase):
    def test_all_v02_environments_qualify(self):
        self.assertGreaterEqual(len(V02), 6)
        for eid in V02:
            with self.subTest(environment=eid):
                self.assertEqual(qualify(eid, 30)["status"], "passed")

    def test_manifest_matches_environment(self):
        for m in manifests():
            env = load(m["id"])
            self.assertEqual(m["contract"], "0.2")
            self.assertEqual(env.interaction, m["interaction"])
            self.assertTrue((load.__globals__["ROOT"] / "environments" / m["id"] / "README.md").is_file())

    def test_invalid_seeds_splits_and_ids_rejected(self):
        env = load("invoice_amount_due")
        for seed in (-1, "1", True):
            with self.assertRaises(ValueError):
                env.reset(seed)
        with self.assertRaises(ValueError):
            env.reset(0, "secret")
        with self.assertRaises(ValueError):
            load("../../untrusted")


class AnswerTests(unittest.TestCase):
    def test_last_svar_line_counts_and_reasoning_is_ignored(self):
        spec = {"type": "money", "value": 12345}
        self.assertEqual(answers.score_answer(spec, "SVAR: 1 kr\nnej vänta\nSVAR: 123,45 kr")["reward"], 1.0)
        self.assertEqual(answers.score_answer(spec, "<think>SVAR: 123,45 kr</think>")["reward"], 0.0)
        self.assertEqual(answers.score_answer(spec, "**SVAR:** 123,45 kr")["reward"], 1.0)
        self.assertEqual(answers.score_answer(spec, "SVAR: 123,45 kr eller 124,00 kr")["reward"], 0.0)

    def test_markdown_and_key_spelling_do_not_matter(self):
        self.assertEqual(answers.score_answer({"type": "money", "value": 254974}, "**SVAR:** 2 549,74 kr")["reward"], 1.0)
        spec = {"type": "mapping", "value": {"leverantor": "Beta", "totalkostnad": {"money": 163525}}}
        self.assertEqual(answers.score_answer(spec, 'SVAR: {"Leverantör": "Beta", "totalkostnad": 1635.25}')["reward"], 1.0)
        self.assertEqual(answers.score_answer(spec, 'SVAR: {"leverantör": "Gamma", "totalkostnad": 1635.25}')["reward"], 0.0)

    def test_abstention_only_when_unanswerable(self):
        self.assertEqual(answers.score_answer({"type": "abstain"}, "SVAR: Information saknas.")["reward"], 1.0)
        self.assertEqual(answers.score_answer({"type": "money", "value": 1}, "SVAR: INFORMATION SAKNAS")["reward"], 0)

    def test_partial_credit_mapping_and_strings(self):
        spec = {"type": "mapping", "value": {"B01": "10", "B02": "omatchad"}, "partial": True}
        self.assertEqual(answers.score_answer(spec, 'SVAR: {"B01": "10", "B02": "11"}')["reward"], 0.5)
        self.assertEqual(answers.score_answer(spec, 'SVAR: {"B01": 10, "B02": "Omatchad", "B03": "x"}')["reward"], 0.5)
        spec = {"type": "strings", "value": ["a", "b", "a"], "partial": True}
        self.assertEqual(answers.score_answer(spec, 'SVAR: ["a", "b", "a"]')["reward"], 1.0)
        self.assertAlmostEqual(answers.score_answer(spec, 'SVAR: ["a", "b"]')["reward"], 0.8)


class DomainTests(unittest.TestCase):
    def test_invoice_amount_due_recomputed_from_prompt(self):
        env = load("invoice_amount_due")
        checked = 0
        for seed in range(200):
            env.reset(seed, "eval")
            prompt = env.public_prompt()
            if "enligt separat offert" in prompt:
                self.assertEqual(env._task.spec["type"], "abstain")
                continue
            total = 0
            for row in re.findall(r"^\| \d+ \|.*\|$", prompt, re.M):
                cells = [c.strip() for c in row.strip("|").split("|")]
                qty, price = int(cells[2]), fmt.parse_money(cells[3])
                vat = int(re.search(r"(\d+) %", cells[4])[1])
                disc = re.search(r"rabatt (\d+) %", cells[4])
                net = qty * price
                if disc:
                    net -= (net * int(disc[1]) * 2 + 100) // 200  # half-up rounding written independently
                total += net + (net * vat * 2 + 100) // 200
            credit = re.search(r"kreditnota på ([\d  ]+,\d{2}) kr", prompt)
            if credit:
                c = fmt.parse_money(credit[1])
                total -= c + (c * 25 * 2 + 100) // 200
            paid = re.search(r"redan betalat ([\d  ]+,\d{2}) kr", prompt)
            if paid:
                total -= fmt.parse_money(paid[1])
            if "avrundas till hela kronor" in prompt:
                total = (total * 2 + 100) // 200 * 100
            self.assertEqual(env.step(f"SVAR: {fmt.money(total)}")["reward"], 1.0, prompt)
            checked += 1
        self.assertGreater(checked, 150)

    def test_payment_matching_rules_reapplied_from_prompt(self):
        env = load("payment_matching")
        for seed in range(200):
            env.reset(seed, "eval")
            prompt = env.public_prompt()
            invoices = [[c.strip() for c in r.strip("|").split("|")]
                        for r in re.findall(r"^\| \d{4} \|.*\|$", prompt, re.M)]
            payments = [[c.strip() for c in r.strip("|").split("|")]
                        for r in re.findall(r"^\| B\d\d \|.*\|$", prompt, re.M)]
            out = {}
            for pid, _, payer, amount, ref in payments:
                ocr_hit = [i for i in invoices if i[3] == ref]
                if ocr_hit and ids.luhn_valid(ref):
                    out[pid] = ocr_hit[0][0]
                    continue
                same = [i for i in invoices if i[1] == payer and fmt.parse_money(i[2]) == fmt.parse_money(amount)]
                out[pid] = same[0][0] if len(same) == 1 else "omatchad"
            self.assertEqual(env.step("SVAR: " + json.dumps(out))["reward"], 1.0, prompt)

    def test_meeting_slot_brute_force_from_prompt(self):
        env = load("meeting_slot")
        for seed in range(150):
            env.reset(seed, "eval")
            prompt = env.public_prompt()
            first, last = re.search(r"mellan (\S+) och (\S+) \(", prompt).groups()
            length = int(re.search(r"möte på (\d+) minuter", prompt)[1])
            buffer = "slutar exakt när" in prompt
            busy = re.findall(r"(\d{4}-\d\d-\d\d) (\d\d):(\d\d)–(\d\d):(\d\d)", prompt)
            d = dt.date.fromisoformat(first)
            answer = "INGEN TID"
            while d <= dt.date.fromisoformat(last) and answer == "INGEN TID":
                if kalender.is_working_day(d):
                    for start in range(8 * 60, 17 * 60 - length + 1, 30):
                        end = start + length
                        if start < 13 * 60 and end > 12 * 60:
                            continue
                        clash = False
                        for bd, h1, m1, h2, m2 in busy:
                            s, e = int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)
                            if bd == d.isoformat() and (s < end and e > start or (buffer and e == start)):
                                clash = True
                        if not clash:
                            answer = f"{d.isoformat()} {start // 60:02d}:{start % 60:02d}"
                            break
                d += dt.timedelta(days=1)
            self.assertEqual(env.step(f"SVAR: {answer}")["reward"], 1.0, prompt)

    def test_redaction_targets_appear_in_text_and_respect_policy(self):
        env = load("document_redaction")
        for seed in range(200):
            env.reset(seed, "eval")
            prompt = env.public_prompt()
            text = prompt.split("--- ÄRENDE ---")[1]
            expected = env._task.spec["value"]
            for item in expected:
                self.assertIn(item, text)
            self.assertNotIn(re.search(r"organisationsnummer (\S+)", text)[1], expected)
            self.assertFalse(any(e.startswith("010-") or e.startswith("registrator@") for e in expected))
            for pnr in re.findall(r"\d{6}-\d{4}", text):
                if not pnr.startswith("55"):
                    self.assertIn(pnr, expected)


    def test_supplier_quotes_rules_reapplied_from_prompt(self):
        env = load("supplier_quotes")
        declined = 0
        for seed in range(300):
            env.reset(seed, "eval")
            prompt = env.public_prompt()
            need = int(re.search(r"Behov: (\d+) enheter", prompt)[1])
            budget = fmt.parse_money(re.search(r"Budget: ([\d \u00a0]+,\d{2}) kr", prompt)[1])
            deadline = int(re.search(r"senast inom (\d+) dagar", prompt)[1])
            best = None
            for row in re.findall(r"^\| [A-Z][a-z]+ – .*\|$", prompt, re.M):
                name, price, ship, days, cap = [c.strip() for c in row.strip("|").split("|")]
                total = need * fmt.parse_money(price) + fmt.parse_money(ship)
                if int(cap) >= need and int(days) <= deadline and total <= budget:
                    key = (total, int(days), name)
                    best = min(best, key) if best else key
            answer = {"leverantor": "avstå"} if best is None else {"leverantor": best[2], "totalkostnad": fmt.money(best[0])}
            declined += best is None
            self.assertEqual(env.step("SVAR: " + json.dumps(answer, ensure_ascii=False))["reward"], 1.0, prompt)
        self.assertGreater(declined, 20)

    def test_inventory_reorder_recomputed_from_prompt(self):
        env = load("inventory_reorder")
        for seed in range(200):
            env.reset(seed, "eval")
            prompt = env.public_prompt()
            cutoff = re.search(r"som kommer senast (\d{4}-\d\d-\d\d)", prompt)[1]
            out = {}
            for row in re.findall(r"^\| A\d{4} \|.*\|$", prompt, re.M):
                number, _, stock, reserved, incoming, minimum, pack = [c.strip() for c in row.strip("|").split("|")]
                counted = sum(int(q) for q, d in re.findall(r"(\d+) st (\d{4}-\d\d-\d\d)", incoming) if d <= cutoff)
                available = int(stock) - int(reserved) + counted
                units = 0
                while available + units < int(minimum):
                    units += int(pack)
                out[number] = units
            self.assertEqual(env.step("SVAR: " + json.dumps(out))["reward"], 1.0, prompt)


class ToolEpisodeTests(unittest.TestCase):
    def test_wrong_state_changes_cost_reward(self):
        env = load("payment_registration")
        for seed in range(60):
            env.reset(seed, "eval")
            ref = env.reference_actions()
            regs = [a for a in ref if a.get("tool") == "registrera_betalning"]
            if not regs:
                continue
            bad = dict(regs[0]["arguments"])
            others = [n for n in env._state.invoices if n != bad["fakturanummer"]]
            bad["fakturanummer"] = others[0]
            actions = [a if a is not regs[0] else {"tool": "registrera_betalning", "arguments": bad} for a in ref]
            self.assertLess(run_actions(env, actions)["reward"], 1.0)

    def test_reschedule_to_wrong_slot_scores_zero(self):
        env = load("meeting_reschedule")
        for seed in range(40):
            env.reset(seed, "eval")
            ref = env.reference_actions()
            move = next(a for a in ref if a.get("tool") == "flytta_mote")
            wrong = dict(move["arguments"], start="16:30" if move["arguments"]["start"] != "16:30" else "08:00")
            actions = [a if a is not move else {"tool": "flytta_mote", "arguments": wrong} for a in ref]
            self.assertEqual(run_actions(env, actions)["reward"], 0.0)

    def test_hermes_text_tool_calls_parse(self):
        actions = parse_assistant('<think>x</think><tool_call>{"name": "lista_personer", "arguments": {}}</tool_call>')
        self.assertEqual(actions, [{"tool": "lista_personer", "arguments": {}}])
        self.assertEqual(parse_assistant("Klart!"), [{"final": "Klart!"}])


class RolloutTests(unittest.TestCase):
    def test_rollout_runner_with_scripted_model(self):
        from svrl import rollout

        class Scripted:
            """Plays the trusted reference through the OpenAI message protocol (tests the runner, not a model)."""
            model = "scripted"

            def __init__(self, env_id, split):
                self.env_id, self.split = env_id, split

            def chat(self, messages, tools=None):
                env = load(self.env_id)
                env.reset(self.seed, self.split)
                if env.interaction == "typed_answer":
                    return {"content": env.reference_completion()}
                done = sum(1 for m in messages if m["role"] == "tool")
                action = env.reference_actions()[done]
                if "final" in action:
                    return {"content": action["final"]}
                return {"content": "", "tool_calls": [{"id": f"c{done}", "type": "function", "function": {
                    "name": action["tool"], "arguments": json.dumps(action["arguments"])}}]}

        for eid in ("invoice_amount_due", "payment_registration", "meeting_reschedule"):
            client = Scripted(eid, "eval")
            for seed in range(5):
                client.seed = seed
                env = load(eid)
                run = rollout.run_typed if env.interaction == "typed_answer" else rollout.run_tools
                self.assertEqual(run(env, client, seed, "eval")["reward"], 1.0, eid)


if __name__ == "__main__":
    unittest.main()
