"""Test parentheses generation for affine expressions (issue #36)."""

import pytest
from parser.astnodes import (
    AffineDimOrSymbol,
    AffineAdd,
    AffineSub,
    AffineMul,
    AffineNeg,
    AffineParens,
)


@pytest.mark.parser
def test_addition_no_parentheses():
    """Addition of two dims should not have parentheses."""
    d = AffineDimOrSymbol("d")
    s = AffineDimOrSymbol("s")
    expr = d + s
    # Should be "d + s"
    assert expr.dump() == "d + s"
    # Should not have AffineParens nodes
    assert isinstance(expr, AffineAdd)
    assert not isinstance(expr.operand_a, AffineParens)
    assert not isinstance(expr.operand_b, AffineParens)


@pytest.mark.parser
def test_multiplication_precedence():
    """Multiplication binds tighter than addition."""
    d = AffineDimOrSymbol("d")
    s = AffineDimOrSymbol("s")
    # d * 2 + s should be "d * 2 + s" (no parentheses)
    expr1 = d * 2 + s
    assert expr1.dump() == "d * 2 + s"
    # d + s * 2 should be "d + s * 2" (no parentheses)
    expr2 = d + s * 2
    assert expr2.dump() == "d + s * 2"


@pytest.mark.parser
def test_parentheses_when_needed():
    """Parentheses should be added when precedence requires."""
    d = AffineDimOrSymbol("d")
    s = AffineDimOrSymbol("s")
    # (d + s) * 2 should have parentheses
    expr1 = (d + s) * 2
    assert expr1.dump() == "(d + s) * 2"
    # 2 * (d + s) should have parentheses
    expr2 = 2 * (d + s)
    assert expr2.dump() == "2 * (d + s)"
    # d - (s - d) should have parentheses
    expr3 = d - (s - d)
    assert expr3.dump() == "d - (s - d)"
    # -(d + s) should have parentheses
    expr4 = -(d + s)
    assert expr4.dump() == "-(d + s)"


@pytest.mark.parser
def test_associativity():
    """Left-associative operators should not add unnecessary parentheses."""
    d = AffineDimOrSymbol("d")
    s = AffineDimOrSymbol("s")
    t = AffineDimOrSymbol("t")
    # (d + s) + t same as d + s + t, no parentheses
    expr1 = d + s + t
    assert expr1.dump() == "d + s + t"
    # d + (s + t) should have parentheses (right operand)
    expr2 = d + (s + t)
    assert expr2.dump() == "d + (s + t)"
    # (d - s) - t same as d - s - t
    expr3 = d - s - t
    assert expr3.dump() == "d - s - t"
    # d - (s - t) should have parentheses
    expr4 = d - (s - t)
    assert expr4.dump() == "d - (s - t)"


@pytest.mark.parser
def test_unary_negation():
    """Unary negation has higher precedence than multiplication."""
    d = AffineDimOrSymbol("d")
    s = AffineDimOrSymbol("s")
    # -d * 2 should be "-d * 2" (no parentheses)
    expr1 = -d * 2
    assert expr1.dump() == "-d * 2"
    # -(d * 2) should be "-(d * 2)" (parentheses)
    expr2 = -(d * 2)
    assert expr2.dump() == "-(d * 2)"
    # -d + s should be "-d + s"
    expr3 = -d + s
    assert expr3.dump() == "-d + s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
