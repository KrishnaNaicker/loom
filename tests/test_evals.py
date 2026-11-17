from evals.run import pass_at_k


def test_pass_at_k():
    assert pass_at_k(3, 0, 1) == 0.0
    assert pass_at_k(3, 3, 3) == 1.0
    assert abs(pass_at_k(3, 1, 1) - 1 / 3) < 1e-9
    assert pass_at_k(3, 1, 3) == 1.0
    assert abs(pass_at_k(5, 2, 2) - 0.7) < 1e-9
