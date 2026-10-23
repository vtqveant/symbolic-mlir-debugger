"""Tests for the constrained debugger expression evaluator."""

import z3
import pytest

from debugger.interpreter.safe_eval import ExpressionError, safe_eval


def test_arithmetic_and_precedence():
    assert safe_eval("1 + 2 * 3", {}) == 7
    assert safe_eval("(1 + 2) * 3", {}) == 9
    assert safe_eval("10 // 3", {}) == 3
    assert safe_eval("10 % 3", {}) == 1


def test_variables_and_booleans():
    env = {"a": 5, "b": 3}
    assert safe_eval("a > b and a == 5", env) is True
    assert safe_eval("not (a < b)", env) is True
    assert safe_eval("a in (4, 5, 6)", env) is True


def test_functions():
    assert safe_eval("min(4, 2, 9)", {}) == 2
    assert safe_eval("max([4, 2, 9])", {}) == 9
    assert safe_eval("abs(-7)", {}) == 7
    assert safe_eval("sum([1, 2, 3])", {}) == 6


def test_z3_expressions():
    a = z3.Int("a")
    b = z3.Int("b")
    expr = safe_eval("a + b", {"a": a, "b": b})
    assert z3.is_int(expr)
    condition = safe_eval("a < b", {"a": a, "b": b})
    assert z3.is_bool(condition)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os')",
        "a.__class__",
        "[x for x in range(3)]",
        "open('/etc/passwd')",
        "a + ",
        "abs(1, 2)",
    ],
)
def test_rejects_unsafe_or_invalid_expressions(expression):
    with pytest.raises(ExpressionError):
        safe_eval(expression, {"a": 1})
