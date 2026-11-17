"""The model <-> tools loop. The model may stop; only the gate can say it is done."""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import anthropic

from . import tools
from .gate import Ratchet, run_gate
from .trace import Trace, cost

RUNS = Path(os.environ.get("LOOM_RUNS", Path(__file__).resolve().parent.parent / "runs"))
SYSTEM = """You are working in a code repository (the current directory) to complete one task.
- Do not edit anything under tests/. The harness discards edits to them.
- You cannot declare the task done. When you stop, the harness runs the tests. If they pass you are done;
  if not, you get the failures and continue. The harness may roll files back to the best earlier state.
- Be brief. Act with tools instead of describing what you would do."""


def _short(args):
    return {k: (v[:200] + f"...[{len(v)} chars]" if isinstance(v, str) and len(v) > 200 else v)
            for k, v in args.items()}


def _log(msg):
    print(f"[loom] {msg}", file=sys.stderr, flush=True)


def _tool_results(ws, resp, step, trace, cut_off):
    results = []
    for b in resp.content:
        if b.type != "tool_use":
            continue
        t0 = time.time()
        if cut_off:  # max_tokens hit mid-call: the input may be partial, so don't run it
            out, err = "error: your response hit max_tokens and this call was cut off; retry smaller", True
        else:
            out, err = tools.call(ws, b.name, b.input)
        trace("tool", step=step, name=b.name, input=_short(b.input), is_error=err, chars=len(out),
              ms=int((time.time() - t0) * 1000))
        _log(f"step {step}: {b.name} {'ERR' if err else 'ok'}")
        results.append({"type": "tool_result", "tool_use_id": b.id, "content": out, "is_error": err})
    return results


def run(task_dir, gate=True, max_steps=40, max_cost=0.50, max_gates=5):
    task_dir = Path(task_dir).resolve()
    model = os.environ.get("LOOM_MODEL")
    if not model:
        raise SystemExit("LOOM_MODEL is not set (see .env.example)")
    ws = tempfile.mkdtemp(prefix="loom-ws-")
    shutil.copytree(task_dir / "repo", ws, dirs_exist_ok=True)
    shutil.copytree(task_dir / "tests", Path(ws) / "tests")
    trace = Trace(RUNS / f"{time.strftime('%Y%m%d-%H%M%S')}-{task_dir.name}-{os.getpid()}.jsonl")
    trace("start", task=task_dir.name, model=model, workspace=ws, gate=gate)
    ratchet = Ratchet()
    if gate:
        g = run_gate(ws, task_dir)
        trace("gate", step=0, n=0, action=ratchet.update(ws, g), **{k: g[k] for k in ("passed", "failed", "green")})

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": (task_dir / "instruction.md").read_text()}]
    steps = gates = tin = tout = 0
    spent, status, reason = 0.0, "fail", "max_steps"
    while steps < max_steps:
        steps += 1
        try:
            resp = client.messages.create(model=model, max_tokens=16000, system=SYSTEM,
                                          tools=tools.schemas(), messages=messages)
        except anthropic.APIError as e:
            status, reason = "error", f"api: {type(e).__name__}: {e}"
            break
        c = cost(model, resp.usage)
        spent += c or 0
        tin, tout = tin + resp.usage.input_tokens, tout + resp.usage.output_tokens
        text = " ".join(b.text for b in resp.content if b.type == "text")
        trace("model", step=steps, stop_reason=resp.stop_reason, usage=resp.usage.model_dump(), cost=c, text=text[:500])
        messages.append({"role": "assistant", "content": resp.content})  # append-only, thinking included

        if resp.stop_reason in ("tool_use", "max_tokens"):
            results = _tool_results(ws, resp, steps, trace, cut_off=resp.stop_reason == "max_tokens")
            if resp.stop_reason == "max_tokens":
                results.append({"type": "text", "text": "Your response was cut off at max_tokens. Continue."})
            messages.append({"role": "user", "content": results})
        elif resp.stop_reason == "refusal":
            status, reason = "fail", "refusal"
            break
        elif not gate:  # A/B mode: the model's stop is taken at its word
            status, reason = "stopped", "model_stopped"
            break
        else:  # the model wants to stop: the gate decides
            gates += 1
            g = run_gate(ws, task_dir)
            action = ratchet.update(ws, g)
            trace("gate", step=steps, n=gates, action=action, tampered=g["tampered"],
                  **{k: g[k] for k in ("passed", "failed", "green")})
            _log(f"gate {gates}: {g['passed']} passed, {g['failed']} failed -> {action}")
            if g["green"]:
                status, reason = "pass", "gate_green"
                break
            if gates >= max_gates:
                reason = "max_gates"
                break
            note = f"\nThe workspace was rolled back to the best earlier state ({ratchet.best} passing)." \
                if action == "rollback" else ""
            if g["tampered"]:
                note += "\nYour edits to tests/ were discarded. Fix the code, not the tests."
            messages.append({"role": "user", "content": f"Not done. The harness ran the tests: {g['passed']} "
                             f"passed, {g['failed']} failed.{note}\n\n{g['output']}"})
        if spent > max_cost:
            reason = "max_cost"
            break

    if gate and status == "fail":  # budget ran out: one last gate, else leave the best snapshot
        g = run_gate(ws, task_dir)
        if g["green"]:
            status, reason = "pass", reason + "+final_gate_green"
        else:
            ratchet.restore(ws)
        trace("gate", step=steps, n=gates + 1, action="final", **{k: g[k] for k in ("passed", "failed", "green")})
    shutil.rmtree(ratchet.snap, ignore_errors=True)
    summary = {"status": status, "reason": reason, "task": task_dir.name, "steps": steps, "gates": gates,
               "input_tokens": tin, "output_tokens": tout, "cost": round(spent, 6), "workspace": ws,
               "trace": str(trace.path)}
    trace("end", **summary)
    return summary
