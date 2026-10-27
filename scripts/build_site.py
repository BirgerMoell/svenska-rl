"""Build static catalogue and agent-readable entry points; --check detects drift."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from svrl.core import manifests, source_digest


def outputs():
    tasks = json.loads((ROOT / 'catalogue/tasks.json').read_text())
    taxonomy = json.loads((ROOT / 'catalogue/taxonomy.json').read_text())
    skill = (ROOT / '.agents/skills/contribute-svenska-rl/SKILL.md').read_text()
    catalogue = {'target': taxonomy['target_environments'], 'areas': taxonomy['areas'],
                 'environments': manifests(), 'tasks': tasks,
                 'source_sha256': source_digest()}
    return {'catalogue.json': json.dumps(catalogue, ensure_ascii=False, indent=2) + '\n',
            'SKILL.md': skill,
            'llms.txt': '# Svenska RL\n\nAgent contribution entry point.\n\n'
                        '- [Contribution skill](https://birgermoell.github.io/svenska-rl/SKILL.md)\n'
                        '- [Repository](https://github.com/BirgerMoell/svenska-rl)\n'
                        '- [Task catalogue](https://birgermoell.github.io/svenska-rl/catalogue.json)\n',
            '.nojekyll': ''}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    drift = []
    for name, content in outputs().items():
        path = ROOT / 'site' / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                drift.append(name)
        else:
            path.write_text(content)
    if drift:
        raise SystemExit('Regenerate site: python3 scripts/build_site.py; drift: ' + ', '.join(drift))
    print('Site assets current.' if args.check else 'Site assets generated.')


if __name__ == '__main__':
    main()
