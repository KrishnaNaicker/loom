"""Eval runner. Launches loom as a subprocess per task, grades with hidden tests after the run ends.

It never imports loom. It is the only code that touches tasks' hidden/ dirs.

  uv run python -m evals.run                     # k=3 runs per task, gated
  uv run python -m evals.run --no-gate           # A/B: trust the model's stop
  uv run python -m evals.run --check-solutions   # validate tasks, no model calls
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "evals" / "tasks"


def pytest_ok(ws, d, timeout=120):
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", d],
                           cwd=ws, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0


def grade(task, ws):
    """Pristine visible tests + hidden tests, run in the final workspace."""
    ws = Path(ws)
    for d in ("tests", "hidden"):
        shutil.rmtree(ws / d, ignore_errors=True)
        shutil.copytree(task / d, ws / d)
    return pytest_ok(ws, "tests"), pytest_ok(ws, "hidden")


def pytest_counts(ws, d, timeout=120):
    """Run pytest on d in ws; return (failed, total). Errors count as failures; a run that
    produced no summary (timeout, no tests, crash) counts as 1 of 1 failed."""
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", d],
                           cwd=ws, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, 1
    n = {k: 0 for k in ("passed", "failed", "error", "errors")}
    for count, word in re.findall(r"(\d+) (passed|failed|errors?)\b", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""):
        n[word] += int(count)
    failed, total = n["failed"] + n["error"] + n["errors"], n["passed"] + n["failed"] + n["error"] + n["errors"]
    if total == 0 or (r.returncode != 0 and failed == 0):
        return 1, 1
    return failed, total


def check_variant(t, layers):
    """Build repo + layers in a temp workspace with pristine tests/hidden; return ((vf, vt), (hf, ht))."""
    ws = Path(tempfile.mkdtemp(prefix="loom-check-"))
    try:
        for layer in ["repo", *layers]:
            shutil.copytree(t / layer, ws, dirs_exist_ok=True)
        for d in ("tests", "hidden"):
            shutil.copytree(t / d, ws / d, dirs_exist_ok=True)
        return pytest_counts(ws, "tests"), pytest_counts(ws, "hidden")
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def check_solutions(tasks):
    """A task is valid only if the unfixed repo and the guess overlay each fail >=1 visible and
    >=2 hidden tests, and the oracle (repo + solution) passes everything."""
    ok = True
    fmt = lambda c: f"v={c[0][0]}/{c[0][1]} h={c[1][0]}/{c[1][1]}"
    for t in tasks:
        broken = lambda c: c[0][0] < 1 or c[1][0] < 2
        unfixed = check_variant(t, [])
        oracle = check_variant(t, ["solution"])
        good = not broken(unfixed) and oracle[0][0] == 0 and oracle[1][0] == 0
        if (t / "guess").is_dir():
            guess = check_variant(t, ["guess"])
            good &= not broken(guess)
            gtxt = fmt(guess)
        else:
            gtxt = "skipped (no guess/ dir)"
        ok &= good
        print(f"{t.name:14} unfixed {fmt(unfixed)} | guess {gtxt} | oracle {fmt(oracle)}  "
              f"{'OK' if good else 'BROKEN'}")
    return ok


def run_one(task, no_gate, max_cost):
    cmd = [sys.executable, "-m", "loom", "run", str(task), "--max-cost", str(max_cost)]
    if no_gate:
        cmd.append("--no-gate")
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        lines = p.stdout.strip().splitlines()
        s = json.loads(lines[-1]) if lines else {"status": "error", "reason": p.stderr[-500:]}
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        s = {"status": "error", "reason": repr(e)}
    visible = hidden = False
    if s.get("workspace") and Path(s["workspace"]).is_dir():
        visible, hidden = grade(task, s["workspace"])
        shutil.rmtree(s["workspace"], ignore_errors=True)
    r = {"task": task.name, "status": s.get("status"), "reason": s.get("reason"), "visible": visible,
         "hidden": hidden, "solved": visible and hidden, "cost": s.get("cost") or 0.0,
         "steps": s.get("steps"), "secs": round(time.time() - t0, 1), "trace": s.get("trace")}
    print(f"  {task.name:16} {r['status']:7} visible={visible!s:5} hidden={hidden!s:5} "
          f"${r['cost']:.4f} steps={r['steps']} {r['secs']}s", file=sys.stderr, flush=True)
    return r


def pass_at_k(n, c, k):
    """Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k)."""
    return 1.0 if n - c < k else 1 - math.comb(n - c, k) / math.comb(n, k)


def report(results, tasks, k):
    print(f"\n{'task':16} {'n':>3} {'c':>3} {'vis':>4} {'pass@1':>7} {f'pass@{k}':>7} {'$/run':>8}")
    rows = []
    for t in tasks:
        rs = [r for r in results if r["task"] == t.name]
        n, c, v = len(rs), sum(r["solved"] for r in rs), sum(r["visible"] for r in rs)
        row = {"task": t.name, "n": n, "c": c, "visible": v, "pass@1": pass_at_k(n, c, 1),
               f"pass@{k}": pass_at_k(n, c, k), "cost_per_run": sum(r["cost"] for r in rs) / max(n, 1)}
        rows.append(row)
        print(f"{t.name:16} {n:3} {c:3} {v:4} {row['pass@1']:7.2f} {row[f'pass@{k}']:7.2f} "
              f"{row['cost_per_run']:8.4f}")
    total = sum(r["cost"] for r in results)
    mean = lambda key: sum(r[key] for r in rows) / max(len(rows), 1)
    print(f"{'mean':16} {'':3} {'':3} {'':4} {mean('pass@1'):7.2f} {mean(f'pass@{k}'):7.2f}   total ${total:.4f}")
    print("vis = runs whose visible tests pass; vis > c means the model passed the tests but guessed the definition")
    return rows, total


def main(argv=None):
    ap = argparse.ArgumentParser(prog="evals.run")
    ap.add_argument("-k", type=int, default=3, help="runs per task")
    ap.add_argument("--no-gate", action="store_true")
    ap.add_argument("--check-solutions", action="store_true")
    ap.add_argument("--tasks", nargs="*", help="task names (default: all)")
    ap.add_argument("--max-cost", type=float, default=0.50, help="per-run budget, passed to loom")
    ap.add_argument("-j", type=int, default=4, help="parallel runs")
    a = ap.parse_args(argv)
    tasks = sorted(d for d in TASKS.iterdir() if (d / "instruction.md").exists())
    if a.tasks:
        tasks = [t for t in tasks if t.name in a.tasks]
    if a.check_solutions:
        return 0 if check_solutions(tasks) else 1

    jobs = [t for t in tasks for _ in range(a.k)]
    print(f"{len(jobs)} runs ({len(tasks)} tasks x k={a.k}), gate={'off' if a.no_gate else 'on'}", file=sys.stderr)
    with ThreadPoolExecutor(a.j) as pool:
        results = list(pool.map(lambda t: run_one(t, a.no_gate, a.max_cost), jobs))
    rows, total = report(results, tasks, a.k)
    out = ROOT / "runs" / f"eval-{time.strftime('%Y%m%d-%H%M%S')}{'-nogate' if a.no_gate else ''}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"k": a.k, "gate": not a.no_gate, "total_cost": total, "tasks": rows,
                               "runs": results}, indent=2))
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
