"""The verification gate: the harness, not the model, decides "done"."""
import hashlib
import re
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

from .tools import run_proc, truncate

COUNT = re.compile(r"(\d+) (passed|failed|errors?)\b")
JUNK = shutil.ignore_patterns("__pycache__", ".pytest_cache")


def _digest(d):
    h = hashlib.sha256()
    for f in sorted(Path(d).rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            h.update(str(f.relative_to(d)).encode() + f.read_bytes())
    return h.hexdigest()


def parse(out):
    """Counts from pytest's last summary line. Collection errors count as failures."""
    passed = failed = 0
    for n, kind in COUNT.findall(out.strip().splitlines()[-1] if out.strip() else ""):
        if kind == "passed":
            passed = int(n)
        else:
            failed += int(n)
    return passed, failed


def run_gate(ws, task_dir, timeout=120):
    """Restore the pristine visible tests, run them, report. Edits to tests/ never count."""
    src, dst = Path(task_dir) / "tests", Path(ws) / "tests"
    tampered = dst.exists() and _digest(dst) != _digest(src)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=JUNK)
    code, out = run_proc(f"{shlex.quote(sys.executable)} -m pytest -q -p no:cacheprovider tests", ws, timeout)
    passed, failed = parse(out)
    return {"green": code == 0 and passed > 0 and failed == 0, "passed": passed, "failed": failed,
            "tampered": tampered, "output": truncate(out, 60, 30)}


def _clear(d):
    for c in Path(d).iterdir():
        shutil.rmtree(c) if c.is_dir() else c.unlink()


class Ratchet:
    """Snapshot whenever more tests pass than ever before; roll back when the run spirals."""

    def __init__(self, spiral=2):
        self.snap = tempfile.mkdtemp(prefix="loom-snap-")
        self.best, self.stale, self.spiral = -1, 0, spiral

    def snapshot(self, ws):
        _clear(self.snap)
        shutil.copytree(ws, self.snap, dirs_exist_ok=True, ignore=JUNK)

    def restore(self, ws):
        _clear(ws)
        shutil.copytree(self.snap, ws, dirs_exist_ok=True)

    def update(self, ws, g):
        """Returns the action taken: green | snapshot | rollback | kept."""
        if g["green"]:
            self.snapshot(ws)
            return "green"
        if g["passed"] > self.best:
            self.snapshot(ws)
            self.best, self.stale = g["passed"], 0
            return "snapshot"
        self.stale += 1
        if g["passed"] < self.best or self.stale >= self.spiral:
            self.restore(ws)
            self.stale = 0
            return "rollback"
        return "kept"
