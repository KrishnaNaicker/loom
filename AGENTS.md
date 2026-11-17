# loom

A tiny coding harness: model <-> tools loop, a verification gate, evals. Built to be read in one sitting.

## Stack
- Python 3.12, `uv`. Stdlib + one LLM SDK. No agent frameworks.
- Model and key live in `.env` (git-ignored; `.env.example` shows the shape). loom loads it at runtime with a few lines of stdlib. Never read `.env` into context, print it or log it.

## Commands
- Tests: `uv run pytest -q`
- One run: `uv run python -m loom run <task_dir>`
- Evals: `uv run python -m evals.run` (`--no-gate` for the A/B)

## Layout
- `loom/`: the harness (loop, tools, gate, trace, cli)
- `evals/tasks/<name>/`: instruction.md, repo/, tests/, hidden/, solution/
- `evals/run.py`: the eval runner. It shells out to the loom CLI and never imports loom.
- `runs/`: JSONL traces, one file per run (git-ignored)

## Rules (each one is a mistake I've seen)
- The harness decides "done", not the model. Done = the gate ran the tests and they passed.
- Never read, list or copy anything under `evals/*/hidden/` from loom code. Only the eval runner touches it, and only after the run ends.
- Never edit tests to make them pass. Tests are the oracle.
- Never special-case task names or expected answers. The harness must not know which tasks exist.
- Tool errors return text the model can act on ("not found", "matched 3 times"). They never raise and kill the run.
- Tools are plain functions + a JSON schema in a dict. No base classes, no plugin registry.
- No Docker today: a temp workspace per run, subprocess with timeout, kill the process group on timeout.
- Long tool output: keep head + tail, always keep lines with `Error` or `FAILED`.
- Keep `loom/` under ~500 lines. If a change adds a lot, say why first.
- No new dependencies without asking.

## Before saying something works
- Run `uv run pytest -q` and show the result. "Should work" doesn't count.
