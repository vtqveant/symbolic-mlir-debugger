#!/usr/bin/env python3
"""
Index dialect execution handlers.

Handles operations: add, sub, mul, div, rem, and, or, xor, shifts, constant, etc.
"""

from .base import BinaryOperationHandler, ConstantOperationHandler


# Index arithmetic operations reuse binary operation handlers
class IndexAddOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l + r)


class IndexSubOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l - r)


class IndexMulOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l * r)


class IndexDivSOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l / r)  # Signed division


class IndexDivUOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l / r)  # Unsigned division (simplified)


class IndexRemSOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l % r)  # Signed remainder


class IndexRemUOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l % r)  # Unsigned remainder (simplified)


class IndexAndOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l & r)  # Bitwise AND (Z3 doesn't have)


class IndexOrOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l | r)  # Bitwise OR (Z3 doesn't have)


class IndexXorOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l ^ r)  # Bitwise XOR (Z3 doesn't have)


class IndexShiftLeftOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l << r)  # Shift left (Z3 doesn't have)


class IndexShiftRightSignedOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(operator=lambda l, r: l >> r)  # Shift right (Z3 doesn't have)


class IndexShiftRightUnsignedOpHandler(BinaryOperationHandler):
    def __init__(self):
        super().__init__(
            operator=lambda l, r: l >> r
        )  # Unsigned shift (Z3 doesn't have)


# Index constant operations
class IndexConstantOpHandler(ConstantOperationHandler):
    """Handler for index.constant operation."""

    pass


class IndexBoolConstantOpHandler(ConstantOperationHandler):
    """Handler for index.bool_constant operation."""

    pass


# Function to register all index dialect handlers
def register_handlers(registry) -> None:
    """Register index dialect handlers with registry."""
    registry.register("index.add", IndexAddOpHandler())
    registry.register("index.sub", IndexSubOpHandler())
    registry.register("index.mul", IndexMulOpHandler())
    registry.register("index.divs", IndexDivSOpHandler())
    registry.register("index.divu", IndexDivUOpHandler())
    registry.register("index.rems", IndexRemSOpHandler())
    registry.register("index.remu", IndexRemUOpHandler())
    registry.register("index.and", IndexAndOpHandler())
    registry.register("index.or", IndexOrOpHandler())
    registry.register("index.xor", IndexXorOpHandler())
    registry.register("index.shift_left", IndexShiftLeftOpHandler())
    registry.register("index.shift_right_signed", IndexShiftRightSignedOpHandler())
    registry.register("index.shift_right_unsigned", IndexShiftRightUnsignedOpHandler())
    registry.register("index.constant", IndexConstantOpHandler())
    registry.register("index.bool_constant", IndexBoolConstantOpHandler())
