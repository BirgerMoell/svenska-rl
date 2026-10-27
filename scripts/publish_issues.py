"""Idempotent bounded issue publishing. Dry-run unless --apply is explicit."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = 'BirgerMoell/svenska-rl'


def body(task):
    checks = '\n'.join('- [ ] ' + text for text in task['acceptance_checks'])
    details = ''
    for key, heading in (('inputs', 'Indata och observationer'), ('objective', 'Agentens uppgift'),
                         ('verifier', 'Verifiering'), ('variation', 'Datavariation'),
                         ('evaluation', 'Träning och eval')):
        if task.get(key):
            details += f"## {heading}\n{task[key]}\n\n"
    if task.get('edge_cases'):
        details += '## Obligatoriska gränsfall\n' + '\n'.join('- ' + c for c in task['edge_cases']) + '\n\n'
    if task.get('resources'):
        details += '## Beräkningsresurser\n' + '\n'.join(
            f'- **{level}**: {text}' for level, text in task['resources'].items()) + '\n\n'
    return (f"<!-- svrl-task: {task['id']} -->\n\n"
            f"## Uppdrag\n{task['instructions']}\n\n"
            f"Arbetsområde: `{task['area']}` · Arbetsflöde: {task['workflow']}\n\n"
            "## Agentstart\nLäs https://birgermoell.github.io/svenska-rl/SKILL.md. "
            "Kommentera `/claim` och invänta botens bekräftelse innan arbete. "
            "Anspråket gäller 24 timmar; `/renew` förlänger och `/release` frigör.\n\n"
            f"{details}## Godkänt bidrag\n{checks}\n\n"
            "Följ `docs/environment-contract.md` och `docs/validation.md`. "
            "Välj minsta men domäntrogna avgränsning. Om flerstegstillstånd behövs, "
            "föreslå ett uttryckligt runtime-beroende i stället för att förenkla till orelaterad trivia.\n\n"
            "L1: kontrakt + domäntester + liten neural policy. L2: verklig RL-träning "
            "av >=100M modell med loss/gradienter och ändrade vikter. L3: matchad "
            "held-out-eval med statistiskt belagd förbättring. Ej körda nivåer är pending.\n\n"
            "Bidragsgivaren behöver inte skriva kod eller granska manuellt. Agenten "
            "skickar en PR med `Closes #NUMMER` och faktisk evidens.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    tasks = json.loads((ROOT / 'catalogue/tasks.json').read_text())
    if args.limit < 1:
        parser.error('--limit must be positive')
    if len({t['id'] for t in tasks}) != len(tasks) or len({t['title'] for t in tasks}) != len(tasks):
        raise ValueError('duplicate task ids or titles; refusing to publish')
    existing = []
    if args.apply:
        raw = subprocess.check_output(['gh', 'api', '--paginate', '--slurp',
            f'repos/{REPO}/issues?state=all&per_page=100'], text=True)
        existing = [issue for page in json.loads(raw) for issue in page if 'pull_request' not in issue]
    for task in tasks[:args.limit]:
        marker = f"<!-- svrl-task: {task['id']} -->"
        found = next((i for i in existing if marker in (i.get('body') or '')), None)
        if found:
            task['issue_url'] = found['html_url']
        elif args.apply:
            result = subprocess.check_output(['gh', 'issue', 'create', '--repo', REPO,
                '--title', 'Bygg en RL-miljö: ' + task['title'], '--body-file', '-'],
                input=body(task), text=True).strip()
            task['issue_url'] = result
        if args.apply:
            # Checkpoint every issue, so interrupted runs retain published URLs.
            (ROOT / 'catalogue/tasks.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + '\n')
        print(task['id'], task.get('issue_url', '[dry run]'), flush=True)


if __name__ == '__main__':
    main()
