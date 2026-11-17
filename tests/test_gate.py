from loom import gate


def test_parse_pytest_summary():
    assert gate.parse("..F\n1 failed, 2 passed in 0.03s") == (2, 1)
    assert gate.parse("....\n4 passed in 0.01s") == (4, 0)
    assert gate.parse("E ImportError\n1 error in 0.05s") == (0, 1)
    assert gate.parse("2 failed, 1 passed, 1 error in 0.1s") == (1, 3)
    assert gate.parse("") == (0, 0)


def _ws(tmp_path, text):
    (tmp_path / "m.py").write_text(text)
    return tmp_path


def test_ratchet_snapshots_on_improvement_and_rolls_back_on_regression(tmp_path):
    r = gate.Ratchet(spiral=2)
    ws = _ws(tmp_path, "v1")
    assert r.update(ws, {"green": False, "passed": 0}) == "snapshot"  # baseline
    _ws(tmp_path, "v2")
    assert r.update(ws, {"green": False, "passed": 2}) == "snapshot"
    _ws(tmp_path, "v3-broken")
    assert r.update(ws, {"green": False, "passed": 1}) == "rollback"
    assert (tmp_path / "m.py").read_text() == "v2"


def test_ratchet_rolls_back_after_stale_gates(tmp_path):
    r = gate.Ratchet(spiral=2)
    ws = _ws(tmp_path, "v1")
    r.update(ws, {"green": False, "passed": 1})
    _ws(tmp_path, "v2")
    assert r.update(ws, {"green": False, "passed": 1}) == "kept"
    (tmp_path / "junk.py").write_text("x")
    assert r.update(ws, {"green": False, "passed": 1}) == "rollback"
    assert (tmp_path / "m.py").read_text() == "v1" and not (tmp_path / "junk.py").exists()


def test_run_gate_uses_pristine_tests(tmp_path):
    task, ws = tmp_path / "task", tmp_path / "ws"
    (task / "tests").mkdir(parents=True)
    (task / "tests" / "test_a.py").write_text("from m import f\ndef test_f():\n    assert f() == 1\n")
    ws.mkdir()
    (ws / "m.py").write_text("def f():\n    return 2\n")
    (ws / "tests").mkdir()
    (ws / "tests" / "test_a.py").write_text("def test_f():\n    assert True\n")  # the model "fixed" the test
    g = gate.run_gate(ws, task)
    assert g["tampered"] and not g["green"] and g["failed"] == 1
    (ws / "m.py").write_text("def f():\n    return 1\n")
    g = gate.run_gate(ws, task)
    assert g["green"] and g["passed"] == 1 and not g["tampered"]
