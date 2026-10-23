"""A deliberately small expression evaluator for debugger expressions.

The debugger accepts expressions from clients (including automated agents).
Python's ``eval`` is not an acceptable primitive for that. This module parses
an expression with :mod:`ast` and evaluates only a small allow-list of integer
and boolean operations. It works with both concrete Python values and Z3
expressions.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable, Dict, List, Optional

import z3


class ExpressionError(ValueError):
    """Raised when an expression is invalid or uses unsupported syntax."""


_BIN_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_COMPARE_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
}


def _is_z3(value: Any) -> bool:
    return isinstance(value, z3.ExprRef)


def _and(values: List[Any]) -> Any:
    if any(_is_z3(v) for v in values):
        return z3.And(*values)
    return all(values)


def _or(values: List[Any]) -> Any:
    if any(_is_z3(v) for v in values):
        return z3.Or(*values)
    return any(values)


def _not(value: Any) -> Any:
    return z3.Not(value) if _is_z3(value) else not value


def _abs(value: Any) -> Any:
    if _is_z3(value):
        return z3.If(value >= 0, value, -value)
    return abs(value)


def _flatten_args(args: List[Any]) -> List[Any]:
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return list(args[0])
    return args


def _min_max(args: List[Any], want_min: bool) -> Any:
    values = _flatten_args(args)
    if not values:
        raise ExpressionError("min/max requires at least one argument")
    if not any(_is_z3(v) for v in values):
        return min(values) if want_min else max(values)
    result = values[0]
    for value in values[1:]:
        if want_min:
            result = z3.If(result <= value, result, value)
        else:
            result = z3.If(result >= value, result, value)
    return result


def _sum(args: List[Any]) -> Any:
    values = _flatten_args(args)
    total: Any = 0
    for value in values:
        total = total + value
    return total


_FUNCTIONS: Dict[str, Callable[[List[Any]], Any]] = {
    "abs": lambda args: _abs(_single_arg(args, "abs")),
    "min": lambda args: _min_max(args, True),
    "max": lambda args: _min_max(args, False),
    "sum": _sum,
}


def _single_arg(args: List[Any], name: str) -> Any:
    if len(args) != 1:
        raise ExpressionError(f"{name} requires exactly one argument")
    return args[0]


class _Evaluator:
    def __init__(self, env: Dict[str, Any]):
        self.env = env

    def eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, bool)):
                return node.value
            raise ExpressionError(f"unsupported constant: {node.value!r}")
        if isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise ExpressionError(f"access to private name '{node.id}' is not allowed")
            if node.id not in self.env:
                raise ExpressionError(f"unknown variable '{node.id}'")
            return self.env[node.id]
        if isinstance(node, ast.BinOp):
            fn = _BIN_OPS.get(type(node.op))
            if fn is None:
                raise ExpressionError(f"unsupported operator: {type(node.op).__name__}")
            left = self.eval(node.left)
            right = self.eval(node.right)
            try:
                return fn(left, right)
            except ZeroDivisionError as exc:
                raise ExpressionError("division by zero") from exc
        if isinstance(node, ast.UnaryOp):
            value = self.eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return +value
            if isinstance(node.op, ast.Not):
                return _not(value)
            raise ExpressionError(f"unsupported unary operator: {type(node.op).__name__}")
        if isinstance(node, ast.BoolOp):
            values = [self.eval(v) for v in node.values]
            return _and(values) if isinstance(node.op, ast.And) else _or(values)
        if isinstance(node, ast.Compare):
            left = self.eval(node.left)
            conditions = []
            for op, comparator in zip(node.ops, node.comparators):
                fn = _COMPARE_OPS.get(type(op))
                if fn is None:
                    raise ExpressionError(f"unsupported comparison: {type(op).__name__}")
                right = self.eval(comparator)
                conditions.append(fn(left, right))
                left = right
            return _and(conditions)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
                raise ExpressionError("only abs/min/max/sum calls are allowed")
            if node.keywords:
                raise ExpressionError("keyword arguments are not allowed")
            args = [self.eval(arg) for arg in node.args]
            return _FUNCTIONS[node.func.id](args)
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self.eval(elt) for elt in node.elts]
        raise ExpressionError(f"unsupported expression: {type(node).__name__}")


def safe_eval(expression: str, env: Optional[Dict[str, Any]] = None) -> Any:
    """Evaluate a constrained Python-like expression.

    Supported: integers/booleans, names, + - * / // % **, unary +/-/not,
    and/or, comparisons, lists/tuples, and abs/min/max/sum.
    Attributes, subscripts, comprehensions, lambdas, imports, and arbitrary
    calls are rejected.
    """
    if not expression or not expression.strip():
        raise ExpressionError("empty expression")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"syntax error: {exc.msg}") from exc
    return _Evaluator(dict(env or {})).eval(tree.body)
