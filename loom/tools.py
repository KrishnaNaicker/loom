"""The four tools. Plain functions + JSON schemas. Errors come back as text, never raise."""
import os
import re
import signal
import subprocess
from pathlib import Path

KEEP = re.compile(r"Error|FAILED")


def truncate(text, head=80, tail=80):
    """Keep head + tail lines; from the middle keep only lines mentioning Error/FAILED."""
    lines = text.splitlines()
    if len(lines) <= head + tail:
        return text
    middle = [l for l in lines[head:-tail] if KEEP.search(l)]
    cut = len(lines) - head - tail - len(middle)
    return "\n".join(lines[:head] + middle + [f"... [{cut} lines cut] ..."] + lines[-tail:])


def run_proc(cmd, cwd, timeout):
    """Run a shell command in its own process group; kill the whole group on timeout."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC")}  # no keys for the model
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, start_new_session=True, env=env)
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
        return None, (out or "") + f"\n[timed out after {timeout}s, process group killed]"


def _resolve(ws, path):
    p = (Path(ws) / path).resolve()
    if not p.is_relative_to(Path(ws).resolve()):
        return None
    return p


def read(ws, path, offset=0, limit=400):
    p = _resolve(ws, path)
    if p is None:
        return f"error: {path} is outside the workspace"
    if p.is_dir():
        return "\n".join(sorted(c.name + ("/" if c.is_dir() else "") for c in p.iterdir())) or "(empty dir)"
    if not p.exists():
        return f"error: {path} not found"
    lines = p.read_text(errors="replace").splitlines()
    chunk = lines[offset:offset + limit]
    body = "\n".join(f"{i + offset + 1:5}  {l}" for i, l in enumerate(chunk))
    more = len(lines) - offset - len(chunk)
    return body + (f"\n... {more} more lines (use offset)" if more > 0 else "")


def write(ws, path, content):
    p = _resolve(ws, path)
    if p is None:
        return f"error: {path} is outside the workspace"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content.splitlines())} lines to {path}"


def edit(ws, path, old, new):
    p = _resolve(ws, path)
    if p is None:
        return f"error: {path} is outside the workspace"
    if not p.is_file():
        return f"error: {path} not found"
    text = p.read_text()
    n = text.count(old)
    if n == 0:
        return f"error: old text not found in {path}; read the file and copy the text exactly"
    if n > 1:
        return f"error: old text matched {n} times in {path}; include more surrounding lines so it is unique"
    p.write_text(text.replace(old, new, 1))
    return f"edited {path}"


def bash(ws, cmd, timeout=60):
    code, out = run_proc(cmd, ws, min(int(timeout), 300))
    return truncate(f"$ {cmd}\n{out}\n[exit {code}]")


def _schema(desc, props, required):
    return {"description": desc, "input_schema": {"type": "object", "properties": props, "required": required}}


S, I = {"type": "string"}, {"type": "integer"}
TOOLS = {
    "read": (read, _schema("Read a file (numbered lines) or list a directory, relative to the workspace.",
                           {"path": S, "offset": I, "limit": I}, ["path"])),
    "write": (write, _schema("Create or overwrite a file.", {"path": S, "content": S}, ["path", "content"])),
    "edit": (edit, _schema("Replace one exact, unique occurrence of `old` with `new` in a file.",
                           {"path": S, "old": S, "new": S}, ["path", "old", "new"])),
    "bash": (bash, _schema("Run a shell command in the workspace root. Output is truncated.",
                           {"cmd": S, "timeout": I}, ["cmd"])),
}


def schemas():
    return [{"name": name, **spec} for name, (_, spec) in TOOLS.items()]


def call(ws, name, args):
    """Dispatch a tool call. Returns (text, is_error); never raises."""
    if name not in TOOLS:
        return f"error: unknown tool {name}; tools are {', '.join(TOOLS)}", True
    try:
        out = TOOLS[name][0](ws, **args)
    except TypeError as e:
        return f"error: bad arguments for {name}: {e}", True
    except Exception as e:  # a tool bug must not kill the run
        return f"error: {name} failed: {type(e).__name__}: {e}", True
    return out, out.startswith("error:")
