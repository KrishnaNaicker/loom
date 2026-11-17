"""CLI: `python -m loom run <task_dir>`. Progress on stderr, one JSON summary line on stdout."""
import argparse
import json
import os
from pathlib import Path

from . import loop


def load_env(path):
    """Minimal .env loader. Values go into os.environ only; nothing is printed or logged."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="loom")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run one task in a throwaway workspace")
    r.add_argument("task_dir")
    r.add_argument("--no-gate", action="store_true", help="trust the model's stop (A/B baseline)")
    r.add_argument("--max-steps", type=int, default=40)
    r.add_argument("--max-cost", type=float, default=0.50)
    a = ap.parse_args(argv)
    load_env(Path(__file__).resolve().parent.parent / ".env")
    try:
        s = loop.run(a.task_dir, gate=not a.no_gate, max_steps=a.max_steps, max_cost=a.max_cost)
    except Exception as e:
        print(json.dumps({"status": "error", "reason": f"{type(e).__name__}: {e}"}))
        return 2
    print(json.dumps(s))
    return 0 if s["status"] in ("pass", "stopped") else 1
