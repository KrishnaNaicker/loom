# loom
A tiny coding harness. A model (Haiku 5.5) works in a throwaway copy of a task repo with four tools: read, write, edit and bash. It cannot declare itself done: when it stops, the harness runs the visible tests. All green ends the run, more passing tests than before takes a snapshot, and a drop or two stalls in a row rolls back to the best snapshot. Every step, tool call, token and dollar goes to `runs/*.jsonl`.

Setup: `uv sync`, then copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY` and `LOOM_MODEL`. Tests: `uv run pytest -q`.
One run: `uv run python -m loom run evals/tasks/dau`. Progress goes to stderr, and a single JSON summary line to stdout.
Evals: `uv run python -m evals.run -k 3`. Add `--no-gate` for the A/B, or `--check-solutions` to check the tasks without calling the model. The runner launches loom as a subprocess and grades with hidden tests only after the run ends.

Results on 3 "certified metrics" tasks (dau, net_revenue, d7_retention), k=3: pass@1 = pass@3 = 1.00 both with the gate and without it, at about $0.002 per run.
Why the delta is 0: Haiku finds METRICS.md on its own and gets the definition right on its first stop in all 18 runs, so the gate never has a failure to send back. A gate only helps when first attempts are sometimes wrong, and these tasks are too small for that.

Not built: no Docker (bash runs on the host in a temp dir, so a model could reach outside it), no context compaction (runs are a few steps long), no todo tool, no prompt caching.
