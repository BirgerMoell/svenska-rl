import argparse
import json

from svrl.core import load, manifests
from svrl.validation import save_report, validate


def main():
    parser = argparse.ArgumentParser(prog="svrl")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    demo = commands.add_parser("demo")
    demo.add_argument("environment")
    demo.add_argument("--seed", type=int, default=0)
    check = commands.add_parser("check")
    check.add_argument("environment")
    check.add_argument("--cases", type=int, default=100)
    check.add_argument("--output", default="runs/contract.json")
    smoke = commands.add_parser("smoke")
    smoke.add_argument("environment")
    smoke.add_argument("--output", default="runs/l1.json")
    train = commands.add_parser("train")
    train.add_argument("environment")
    train.add_argument("--model", required=True)
    train.add_argument("--revision", required=True)
    train.add_argument("--output-dir", required=True)
    train.add_argument("--steps", type=int, default=20)
    train.add_argument("--batch-size", type=int, default=4)
    train.add_argument("--eval-cases", type=int, default=64)
    train.add_argument("--learning-rate", type=float, default=1e-5)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--device", default="cpu")
    train.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps(manifests(), ensure_ascii=False, indent=2))
    elif args.command == "demo":
        env = load(args.environment)
        env.reset(args.seed, "dev")
        print(env.public_prompt())
    elif args.command == "check":
        report = save_report(args.output, {"level": "contract", "environment": args.environment,
                                           **validate(args.environment, args.cases)})
        print(json.dumps(report, indent=2))
    elif args.command == "smoke":
        from svrl.learning import smoke
        print(json.dumps(smoke(args.environment, args.output), indent=2))
    elif args.command == "train":
        from svrl.learning import train
        report = train(args.environment, args.model, args.revision, args.output_dir,
                       args.steps, args.batch_size, args.eval_cases, args.learning_rate,
                       args.seed, args.device, args.threads)
        print(json.dumps({k: report[k] for k in ("level", "l3_outcome", "paired_improvement")}, indent=2))


if __name__ == "__main__":
    main()
