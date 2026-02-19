# Arithmetic Dialect Operations Documentation

## Overview
This document provides a comprehensive list of all operations in the MLIR Arithmetic (arith) dialect, based on MLIR documentation, source code, and existing usage in the symbolic-mlir-debugger repository.

## Operation Categories

### 1. Integer Arithmetic Operations

#### `arith.addi` - Integer Addition
- **Description**: Integer addition operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (sum)
- **Attributes**: None
- **Examples**:
  ```mlir
  %sum = arith.addi %a, %b : i32
  %sum64 = arith.addi %x, %y : i64
  ```
- **Constraints**: May overflow (depends on bitwidth)

#### `arith.subi` - Integer Subtraction
- **Description**: Integer subtraction operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (difference)
- **Attributes**: None
- **Examples**:
  ```mlir
  %diff = arith.subi %a, %b : i32
  ```

#### `arith.muli` - Integer Multiplication
- **Description**: Integer multiplication operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (product)
- **Attributes**: None
- **Examples**:
  ```mlir
  %prod = arith.muli %a, %b : i32
  ```

#### `arith.divsi` - Signed Integer Division
- **Description**: Signed integer division (rounds toward zero)
- **Operands**: 2 (dividend, divisor)
- **Results**: 1 (quotient)
- **Attributes**: None
- **Examples**:
  ```mlir
  %quot = arith.divsi %a, %b : i32
  ```
- **Constraints**: Division by zero is undefined

#### `arith.divui` - Unsigned Integer Division
- **Description**: Unsigned integer division
- **Operands**: 2 (dividend, divisor)
- **Results**: 1 (quotient)
- **Attributes**: None
- **Examples**:
  ```mlir
  %quot = arith.divui %a, %b : i32
  ```
- **Constraints**: Division by zero is undefined

#### `arith.remsi` - Signed Integer Remainder
- **Description**: Signed integer remainder (sign follows dividend)
- **Operands**: 2 (dividend, divisor)
- **Results**: 1 (remainder)
- **Attributes**: None
- **Examples**:
  ```mlir
  %rem = arith.remsi %a, %b : i32
  ```
- **Constraints**: Division by zero is undefined

#### `arith.remui` - Unsigned Integer Remainder
- **Description**: Unsigned integer remainder
- **Operands**: 2 (dividend, divisor)
- **Results**: 1 (remainder)
- **Attributes**: None
- **Examples**:
  ```mlir
  %rem = arith.remui %a, %b : i32
  ```
- **Constraints**: Division by zero is undefined

### 2. Floating-Point Arithmetic Operations

#### `arith.addf` - Floating-Point Addition
- **Description**: Floating-point addition
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (sum)
- **Attributes**: None
- **Examples**:
  ```mlir
  %sum = arith.addf %a, %b : f32
  %sum64 = arith.addf %x, %y : f64
  ```

#### `arith.subf` - Floating-Point Subtraction
- **Description**: Floating-point subtraction
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (difference)
- **Attributes**: None
- **Examples**:
  ```mlir
  %diff = arith.subf %a, %b : f32
  ```

#### `arith.mulf` - Floating-Point Multiplication
- **Description**: Floating-point multiplication
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (product)
- **Attributes**: None
- **Examples**:
  ```mlir
  %prod = arith.mulf %a, %b : f32
  ```

#### `arith.divf` - Floating-Point Division
- **Description**: Floating-point division
- **Operands**: 2 (dividend, divisor)
- **Results**: 1 (quotient)
- **Attributes**: None
- **Examples**:
  ```mlir
  %quot = arith.divf %a, %b : f32
  ```

### 3. Comparison Operations

#### `arith.cmpi` - Integer Comparison
- **Description**: Integer comparison operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (boolean result)
- **Attributes**: `predicate` (one of: eq, ne, slt, sle, sgt, sge, ult, ule, ugt, uge)
- **Examples**:
  ```mlir
  %cmp = arith.cmpi slt, %a, %b : i32      # signed less than
  %cmp2 = arith.cmpi eq, %x, %y : i64      # equality
  %cmp3 = arith.cmpi ugt, %p, %q : i16     # unsigned greater than
  ```

#### `arith.cmpf` - Floating-Point Comparison
- **Description**: Floating-point comparison operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (boolean result)
- **Attributes**: `predicate` (one of: false, oeq, ogt, oge, olt, ole, one, ord, ueq, ugt, uge, ult, ule, une, uno, true)
- **Examples**:
  ```mlir
  %cmp = arith.cmpf oeq, %a, %b : f32      # ordered equal
  %cmp2 = arith.cmpf ult, %x, %y : f64     # unordered less than
  ```

### 4. Constant Operations

#### `arith.constant` - Constant Value
- **Description**: Constant value operation
- **Operands**: 0
- **Results**: 1 (constant value)
- **Attributes**: `value` (the constant value)
- **Examples**:
  ```mlir
  %c42 = arith.constant 42 : i32
  %c3_14 = arith.constant 3.14 : f32
  %c_true = arith.constant true
  %c_false = arith.constant false
  ```

### 5. Conversion Operations

#### `arith.extsi` - Sign Extension
- **Description**: Sign extension (signed integer to larger signed integer)
- **Operands**: 1 (source)
- **Results**: 1 (extended value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %ext = arith.extsi %a : i16 to i32
  %ext64 = arith.extsi %b : i32 to i64
  ```

#### `arith.extui` - Zero Extension
- **Description**: Zero extension (unsigned integer to larger unsigned integer)
- **Operands**: 1 (source)
- **Results**: 1 (extended value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %ext = arith.extui %a : i16 to i32
  ```

#### `arith.trunci` - Truncation
- **Description**: Integer truncation (larger integer to smaller integer)
- **Operands**: 1 (source)
- **Results**: 1 (truncated value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %trunc = arith.trunci %a : i32 to i16
  %trunc8 = arith.trunci %b : i64 to i8
  ```

#### `arith.sitofp` - Signed Integer to Floating-Point
- **Description**: Convert signed integer to floating-point
- **Operands**: 1 (source integer)
- **Results**: 1 (floating-point value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %fp = arith.sitofp %a : i32 to f32
  %fp64 = arith.sitofp %b : i64 to f64
  ```

#### `arith.uitofp` - Unsigned Integer to Floating-Point
- **Description**: Convert unsigned integer to floating-point
- **Operands**: 1 (source integer)
- **Results**: 1 (floating-point value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %fp = arith.uitofp %a : i32 to f32
  ```

#### `arith.fptosi` - Floating-Point to Signed Integer
- **Description**: Convert floating-point to signed integer (rounds toward zero)
- **Operands**: 1 (source floating-point)
- **Results**: 1 (integer value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %int = arith.fptosi %a : f32 to i32
  ```

#### `arith.fptoui` - Floating-Point to Unsigned Integer
- **Description**: Convert floating-point to unsigned integer (rounds toward zero)
- **Operands**: 1 (source floating-point)
- **Results**: 1 (integer value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %int = arith.fptoui %a : f32 to i32
  ```

### 6. Bitwise Operations

#### `arith.andi` - Bitwise AND
- **Description**: Bitwise AND operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (result)
- **Attributes**: None
- **Examples**:
  ```mlir
  %and = arith.andi %a, %b : i32
  ```

#### `arith.ori` - Bitwise OR
- **Description**: Bitwise OR operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (result)
- **Attributes**: None
- **Examples**:
  ```mlir
  %or = arith.ori %a, %b : i32
  ```

#### `arith.xori` - Bitwise XOR
- **Description**: Bitwise XOR operation
- **Operands**: 2 (lhs, rhs)
- **Results**: 1 (result)
- **Attributes**: None
- **Examples**:
  ```mlir
  %xor = arith.xori %a, %b : i32
  ```

#### `arith.shli` - Shift Left
- **Description**: Shift left operation
- **Operands**: 2 (value, shift amount)
- **Results**: 1 (shifted value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %shifted = arith.shli %a, %shift : i32
  ```

#### `arith.shrsi` - Arithmetic Shift Right
- **Description**: Arithmetic shift right (sign-extending)
- **Operands**: 2 (value, shift amount)
- **Results**: 1 (shifted value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %shifted = arith.shrsi %a, %shift : i32
  ```

#### `arith.shrui` - Logical Shift Right
- **Description**: Logical shift right (zero-extending)
- **Operands**: 2 (value, shift amount)
- **Results**: 1 (shifted value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %shifted = arith.shrui %a, %shift : i32
  ```

### 7. Special Operations

#### `arith.select` - Select Operation
- **Description**: Select between two values based on condition
- **Operands**: 3 (condition, true_value, false_value)
- **Results**: 1 (selected value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %result = arith.select %cond, %true_val, %false_val : i32
  ```

#### `arith.index_cast` - Index Type Casting
- **Description**: Cast between index and integer types
- **Operands**: 1 (source)
- **Results**: 1 (casted value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %int = arith.index_cast %idx : index to i64
  %idx = arith.index_cast %int : i64 to index
  ```

#### `arith.bitcast` - Bitwise Cast
- **Description**: Bitwise cast between types of same bitwidth
- **Operands**: 1 (source)
- **Results**: 1 (casted value)
- **Attributes**: None
- **Examples**:
  ```mlir
  %cast = arith.bitcast %a : i32 to f32  # reinterpret bits
  ```

## Existing Usage in Repository

Based on current MLIR fixtures, the following `arith` operations are already used:

1. **arith.addi** - Integer addition (`arith_basic_ops.mlir`, `arith_mixed_bitwidth.mlir`)
2. **arith.subi** - Integer subtraction (`arith_basic_ops.mlir`)
3. **arith.muli** - Integer multiplication (`arith_basic_ops.mlir`)
4. **arith.divsi** - Signed integer division (`arith_basic_ops.mlir`)
5. **arith.remsi** - Signed integer remainder (`arith_basic_ops.mlir`)
6. **arith.extsi** - Sign extension (`arith_mixed_bitwidth.mlir`)
7. **arith.cmpi** - Integer comparison (`arith_conditional.mlir`, `conditional_branch.mlir`)
8. **arith.constant** - Constant value (various fixtures)
9. **arith.index_cast** - Index type casting (`arith_mixed_bitwidth.mlir`)

## Bitwidth Support

Common bitwidths used in testing:
- **Integer**: 1, 8, 16, 32, 64 bits
- **Floating-point**: 16 (f16), 32 (f32), 64 (f64) bits
- **Index**: platform-dependent (typically 32 or 64 bits)

## Edge Cases to Consider

1. **Overflow/Underflow**: For integer operations with limited bitwidth
2. **Division by Zero**: For `divsi`, `divui`, `divf`, `remsi`, `remui`
3. **NaN/Infinity**: For floating-point operations
4. **Sign Issues**: For signed vs unsigned operations
5. **Type Mismatches**: For conversion operations
6. **Shift Amount Limits**: For shift operations (0 ≤ shift < bitwidth)

## References

1. MLIR Arithmetic Dialect Documentation
2. MLIR Source Code: `mlir/include/mlir/Dialect/Arith/IR/ArithOps.td`
3. Existing test fixtures in `debugger/fixtures/`
4. Generated test traces in `generated_tests/`

## Next Steps

1. Create configuration file based on this documentation
2. Implement configurable generator script
3. Generate individual MLIR files for each operation
4. Create DAP traces using existing generators
5. Validate complete test suite with DAP client