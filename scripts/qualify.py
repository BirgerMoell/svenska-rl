"""Qualify every discovered environment, including new contributions.

v0.1 (four-action multiple choice): L1 tiny-policy smoke run (needs torch).
v0.2 (typed answers, tool episodes): contract qualification with shortcut probes (standard library); model
baselines and L2/L3 use `svrl.cli rollout` / `svrl.cli export` on contributor compute.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from svrl.core import manifests
from svrl.validation import qualify, save_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', default='runs')
    parser.add_argument('--contract', choices=['0.1', '0.2', 'all'], default='all')
    args = parser.parse_args()
    for manifest in manifests():
        version = manifest.get('contract', '0.1')
        if args.contract not in ('all', version):
            continue
        if version == '0.1':
            from svrl.learning import smoke
            target = Path(args.output_dir) / (manifest['id'] + '-l1.json')
            report = smoke(manifest['id'], target)
        else:
            target = Path(args.output_dir) / (manifest['id'] + '-contract.json')
            report = save_report(target, {'level': 'contract', 'environment': manifest['id'],
                                          **qualify(manifest['id'])})
        print(manifest['id'], report['status'], target, flush=True)


if __name__ == '__main__':
    main()
