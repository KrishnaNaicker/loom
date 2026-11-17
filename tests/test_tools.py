import time

from loom import tools


def test_edit_requires_unique_match(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\nx = 1\n")
    out, err = tools.call(str(tmp_path), "edit", {"path": "a.py", "old": "x = 1", "new": "x = 2"})
    assert err and "matched 2 times" in out
    out, err = tools.call(str(tmp_path), "edit", {"path": "a.py", "old": "y", "new": "z"})
    assert err and "not found" in out
    out, err = tools.call(str(tmp_path), "edit", {"path": "a.py", "old": "x = 1\nx = 1", "new": "x = 3"})
    assert not err and (tmp_path / "a.py").read_text() == "x = 3\n"


def test_paths_cannot_escape_workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    for name, args in [("read", {"path": "../secret"}), ("write", {"path": "../x", "content": "hi"}),
                       ("edit", {"path": "/etc/passwd", "old": "a", "new": "b"})]:
        out, err = tools.call(str(ws), name, args)
        assert err and "outside the workspace" in out
    assert not (tmp_path / "x").exists()


def test_read_write_roundtrip_and_missing(tmp_path):
    tools.call(str(tmp_path), "write", {"path": "d/f.txt", "content": "a\nb\n"})
    out, err = tools.call(str(tmp_path), "read", {"path": "d/f.txt"})
    assert not err and "1  a" in out and "2  b" in out
    out, err = tools.call(str(tmp_path), "read", {"path": "nope.txt"})
    assert err and "not found" in out


def test_bad_args_and_unknown_tool_are_text(tmp_path):
    out, err = tools.call(str(tmp_path), "read", {"pth": "x"})
    assert err and "bad arguments" in out
    out, err = tools.call(str(tmp_path), "grep", {})
    assert err and "unknown tool" in out


def test_truncate_keeps_head_tail_and_failures():
    lines = [f"line {i}" for i in range(1000)]
    lines[500] = "FAILED tests/test_x.py::test_y"
    lines[600] = "ValueError: boom"
    out = tools.truncate("\n".join(lines), head=10, tail=10)
    assert "line 0" in out and "line 999" in out
    assert "FAILED tests/test_x.py::test_y" in out and "ValueError: boom" in out
    assert "line 300" not in out


def test_bash_timeout_kills_process_group(tmp_path):
    start = time.time()
    out, err = tools.call(str(tmp_path), "bash", {"cmd": "sleep 30 & sleep 30; echo done", "timeout": 1})
    assert time.time() - start < 10
    assert "timed out" in out and "\ndone" not in out


def test_bash_does_not_see_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    out, _ = tools.call(str(tmp_path), "bash", {"cmd": "env"})
    assert "sk-test-not-real" not in out
