"""Plan or run repeatable HTTP benchmarks. No GPU benchmark is implied by a plan.

Requires only Python 3.10+ to generate a plan. Execution additionally requires
the vLLM benchmark CLI and a separately started, compatible inference server.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from urllib.parse import urlsplit


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="ID exposed by /v1/models")
    parser.add_argument("--tokenizer", required=True, help="fixed local tokenizer")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True,
                        help="new directory; existing directories are rejected")
    parser.add_argument("--concurrency", nargs="+", type=positive, default=[1, 2, 4, 8])
    parser.add_argument("--repeats", type=positive, default=3)
    parser.add_argument("--num-prompts", type=positive, default=64)
    parser.add_argument("--input-len", type=positive, default=512)
    parser.add_argument("--output-len", type=positive, default=256)
    parser.add_argument("--warmups", type=positive, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--request-rate", default="inf",
                        help="inf for a closed-loop concurrency sweep, or requests/s")
    parser.add_argument("--extra-body", type=json.loads, default={},
                        help="JSON object for identical template options in all groups")
    parser.add_argument("--execute", action="store_true",
                        help="actually send requests; otherwise only write a plan")
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        parser.error("--base-url must be an HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error("--base-url must not contain credentials, query or fragment")
    if parsed.path not in ("", "/"):
        parser.error("--base-url must not include an endpoint path")
    if not isinstance(args.extra_body, dict):
        parser.error("--extra-body must be a JSON object")
    if any(k in args.extra_body for k in ("temperature", "max_tokens", "ignore_eos")):
        parser.error("sampling/length controls must not be overridden in --extra-body")
    try:
        rate = float(args.request_rate)
        if not rate > 0:
            raise ValueError
    except ValueError:
        parser.error("--request-rate must be positive or inf")
    concurrencies = list(dict.fromkeys(args.concurrency))
    if max(concurrencies) > args.num_prompts:
        parser.error("--num-prompts must be >= the largest requested concurrency")
    if args.output.exists():
        parser.error("--output already exists; choose a new run directory")
    args.output.mkdir(parents=True)
    # Use the installed CLI executable; module entry points vary by release.
    executable = ["vllm"]
    workload = {
        "dataset": "random", "seed": args.seed, "input_len": args.input_len,
        "output_len": args.output_len, "num_prompts": args.num_prompts,
        "warmups": args.warmups, "temperature": 0, "ignore_eos": True,
        "request_rate": args.request_rate, "extra_body": args.extra_body,
        "tokenizer": args.tokenizer,
    }
    plans = []
    for repeat in range(1, args.repeats + 1):
        # Reverse alternating sweeps to reduce systematic ordering effects.
        order = concurrencies if repeat % 2 else list(reversed(concurrencies))
        for concurrency in order:
            name = f"r{repeat}-c{concurrency}"
            run_dir = args.output / name
            command = executable + [
                "bench", "serve", "--backend", "openai-chat",
                "--base-url", args.base_url, "--endpoint", "/v1/chat/completions",
                "--model", args.model, "--tokenizer", args.tokenizer,
                "--dataset-name", "random", "--seed", str(args.seed),
                "--random-input-len", str(args.input_len),
                "--random-output-len", str(args.output_len),
                "--num-prompts", str(args.num_prompts),
                "--max-concurrency", str(concurrency),
                "--request-rate", args.request_rate,
                "--temperature", "0", "--ignore-eos",
                "--num-warmups", str(args.warmups),
                "--percentile-metrics", "ttft,tpot,itl,e2el",
                "--metric-percentiles", "50,95,99",
                "--save-result", "--save-detailed",
                "--result-dir", str(run_dir), "--result-filename", "result.json",
            ]
            if args.extra_body:
                command += ["--extra-body", json.dumps(args.extra_body)]
            plans.append({"name": name, "command": command})
    manifest = {
        "status": "plan_only", "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "workload": workload,
        "workload_config_sha256": hashlib.sha256(
            json.dumps(workload, sort_keys=True).encode()).hexdigest(),
        "plans": plans,
        "notes": [
            "Random input is a performance workload, not a quality test.",
            "A seed is reproducible only with the same CLI, tokenizer and generator.",
            "This script does not reset caches or collect GPU resource samples.",
            "The workload hash identifies configuration, not exact prompt bytes.",
        ],
    }
    manifest_file = args.output / "manifest.json"

    def save():
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    save()
    if not args.execute:
        print(f"PLAN ONLY: {len(plans)} runs written to {manifest_file}")
        return 0
    try:
        manifest["vllm_package_version"] = importlib.metadata.version("vllm")
        help_result = subprocess.run(
            executable + ["bench", "serve", "--help"],
            capture_output=True, text=True, check=True)
        help_text = help_result.stdout + help_result.stderr
        (args.output / "bench-help.txt").write_text(help_text, encoding="utf-8")
        required = {part for plan in plans for part in plan["command"]
                    if part.startswith("--")}
        # JSON values are individual arguments and never parsed as shell code.
        missing = sorted(flag for flag in required if flag not in help_text)
        if missing:
            raise RuntimeError(f"installed benchmark CLI lacks flags: {missing}")
        manifest["status"] = "running"
        save()
        for plan in plans:
            run_dir = args.output / plan["name"]
            run_dir.mkdir()
            with (run_dir / "benchmark.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(plan["command"], stdout=log,
                                        stderr=subprocess.STDOUT, check=False)
            plan["returncode"] = result.returncode
            save()
            if result.returncode:
                raise RuntimeError(f"{plan['name']} failed; inspect benchmark.log")
            result_file = run_dir / "result.json"
            if not result_file.is_file():
                raise RuntimeError(f"{plan['name']} did not write result.json")
            measured = json.loads(result_file.read_text(encoding="utf-8"))
            if (measured.get("completed") != args.num_prompts
                    or measured.get("failed", 0) != 0
                    or measured.get("duration", 0) <= 0
                    or measured.get("total_output_tokens", 0) <= 0):
                raise RuntimeError(
                    f"{plan['name']} contains incomplete or failed measurements")
            plan["completed"] = measured["completed"]
            save()
        manifest["status"] = "executed"
        save()
        print(f"Executed {len(plans)} runs. Check result.json and quality separately.")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError,
            importlib.metadata.PackageNotFoundError) as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        save()
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
