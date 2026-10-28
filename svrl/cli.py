import argparse
import json

from svrl.core import load, manifests
from svrl.validation import qualify, save_report


def main():
    parser = argparse.ArgumentParser(prog="svrl")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    demo = commands.add_parser("demo")
    demo.add_argument("environment")
    demo.add_argument("--seed", type=int, default=0)
    check = commands.add_parser("check")
    check.add_argument("environment")
    check.add_argument("--cases", type=int, default=None)
    check.add_argument("--output", default="runs/contract.json")
    export = commands.add_parser("export", help="v0.2: write RL training rows (JSONL)")
    export.add_argument("environment")
    export.add_argument("--split", default="train", choices=["train", "dev", "eval"])
    export.add_argument("--count", type=int, default=1000)
    export.add_argument("--start", type=int, default=0)
    export.add_argument("--out", required=True)
    export_hf = commands.add_parser("export-hf", help="v0.2: every environment as a Hugging Face dataset folder")
    export_hf.add_argument("--out", required=True)
    export_hf.add_argument("--count", type=int, default=2000)
    export_hf.add_argument("--eval-count", type=int, default=None)
    rollout = commands.add_parser("rollout", help="v0.2: evaluate an OpenAI-compatible chat model")
    rollout.add_argument("environment")
    rollout.add_argument("--base-url", required=True)
    rollout.add_argument("--model", required=True)
    rollout.add_argument("--api-key", default="EMPTY")
    rollout.add_argument("--split", default="eval", choices=["train", "dev", "eval"])
    rollout.add_argument("--count", type=int, default=64)
    rollout.add_argument("--start", type=int, default=0)
    rollout.add_argument("--workers", type=int, default=4)
    rollout.add_argument("--max-tokens", type=int, default=2048)
    rollout.add_argument("--temperature", type=float, default=0.0)
    rollout.add_argument("--out")
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
        obs = env.reset(args.seed, "dev")
        print(env.public_prompt())
        if "tools" in obs:
            print("\nVerktyg: " + ", ".join(t["function"]["name"] for t in obs["tools"]))
    elif args.command == "check":
        report = save_report(args.output, {"level": "contract", "environment": args.environment,
                                           **qualify(args.environment, args.cases)})
        print(json.dumps(report, indent=2))
    elif args.command == "export":
        from svrl.export import export
        print(json.dumps(export(args.environment, args.split, args.count, args.out, args.start), indent=2))
    elif args.command == "export-hf":
        from svrl.export import export_hf
        print(json.dumps(export_hf(args.out, args.count, args.eval_count), indent=2))
    elif args.command == "rollout":
        from svrl.rollout import ChatClient, rollout
        client = ChatClient(args.base_url, args.model, args.api_key, args.temperature, args.max_tokens)
        print(json.dumps(rollout(args.environment, client, args.split, args.count, args.start, args.workers,
                                 args.out), ensure_ascii=False, indent=2))
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
