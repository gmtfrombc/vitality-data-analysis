import pytest

from app.utils.sandbox import run_snippet


@pytest.mark.skipif(
    hasattr(__import__("os"), "name") and __import__("os").name == "nt",
    reason="signal.alarm not available on Windows",
)
def test_infinite_loop_timeout():  # noqa: D103 – sandbox security
    code = "while True:\n    pass"
    res = run_snippet(code)
    assert isinstance(res, dict) and res.get("error")
    assert "timed out" in res["error"].lower()
