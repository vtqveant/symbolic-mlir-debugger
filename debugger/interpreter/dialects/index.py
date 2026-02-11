#!/usr/bin/env python3
"""
Index dialect execution handlers.

Handles operations: add, sub, mul, div, rem, and, or, xor, shifts, constant, etc.
"""

from .base import BinaryOperationHandler, ConstantOperationHandler


# Index arithmetic operations reuse binary operation handlers
class IndexAddHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l + r)


class IndexSubHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l - r)


class IndexMulHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l * r)


class IndexDivSHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l / r)  # Signed division


class IndexDivUHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l / r)  # Unsigned division (simplified)


class IndexRemSHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l % r)  # Signed remainder


class IndexRemUHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l % r)  # Unsigned remainder (simplified)


class IndexAndHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l & r)  # Bitwise AND (Z3 doesn't have)


class IndexOrHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l | r)  # Bitwise OR (Z3 doesn't have)


class IndexXorHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l ^ r)  # Bitwise XOR (Z3 doesn't have)


class IndexShiftLeftHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l << r)  # Shift left (Z3 doesn't have)


class IndexShiftRightSignedHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l >> r)  # Shift right (Z3 doesn't have)


class IndexShiftRightUnsignedHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(
            operator=lambda l, r: l >> r
        )  # Unsigned shift (Z3 doesn't have)


# Index constant operations
class IndexConstantHandler(ConstantOperationHandler):
    """Handler for index.constant operation."""

    pass


class IndexBoolConstantHandler(ConstantOperationHandler):
    """Handler for index.bool_constant operation."""

    pass


# Function to register all index dialect handlers
def register_handlers(registry) -> None:
    """Register index dialect handlers with registry."""
    registry.register("index.add", IndexAddHandler())
    registry.register("index.sub", IndexSubHandler())
    registry.register("index.mul", IndexMulHandler())
    registry.register("index.divs", IndexDivSHandler())
    registry.register("index.divu", IndexDivUHandler())
    registry.register("index.rems", IndexRemSHandler())
    registry.register("index.remu", IndexRemUHandler())
    registry.register("index.and", IndexAndHandler())
    registry.register("index.or", IndexOrHandler())
    registry.register("index.xor", IndexXorHandler())
    registry.register("index.shift_left", IndexShiftLeftHandler())
    registry.register("index.shift_right_signed", IndexShiftRightSignedHandler())
    registry.register("index.shift_right_unsigned", IndexShiftRightUnsignedHandler())
    registry.register("index.constant", IndexConstantHandler())
    registry.register("index.bool_constant", IndexBoolConstantHandler())
