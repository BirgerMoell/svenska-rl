"""Idempotent bounded issue publishing. Dry-run unless --apply is explicit."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = 'BirgerMoell/svenska-rl'


def body(task):
    checks = '\n'.join('- [ ] ' + text for text in task['acceptance_checks'])
    return (f"<!-- svrl-task: {task['id']} -->\n\n"
            f"## Uppdrag\n{task['instructions']}\n\n"
            f"Arbetsområde: `{task['area']}` · Arbetsflöde: {task['workflow']}\n\n"
            "## Agentstart\nLäs https://birgermoell.github.io/svenska-rl/SKILL.md. "
            "Kommentera `/claim` och invänta botens bekräftelse innan arbete. "
            "Anspråket gäller 24 timmar; `/renew` förlänger och `/release` frigör.\n\n"
            f"## Godkänt bidrag\n{checks}\n\n"
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
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    tasks = json.loads((ROOT / 'catalogue/tasks.json').read_text())
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
        print(task['id'], task.get('issue_url', '[dry run]'))
    if args.apply:
        (ROOT / 'catalogue/tasks.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
