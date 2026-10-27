"""Run L1 for every discovered environment, including new contributions."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from svrl.core import manifests
from svrl.learning import smoke


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', default='runs')
    args = parser.parse_args()
    for manifest in manifests():
        target = Path(args.output_dir) / (manifest['id'] + '-l1.json')
        report = smoke(manifest['id'], target)
        print(manifest['id'], report['status'], target, flush=True)


if __name__ == '__main__':
    main()
