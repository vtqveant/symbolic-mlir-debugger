// Arithmetic operations with mixed bit widths
// Function: mixed_bitwidth(i32 %a, i64 %b, i16 %c) -> i64 %result

module {
  func.func @mixed_bitwidth(%a: i32, %b: i64, %c: i16) -> i64 {
    // Convert to common type (i64)
    %a_ext = arith.extsi %a : i32 to i64
    %c_ext = arith.extsi %c : i16 to i64
    
    // Perform arithmetic with mixed types
    %add1 = arith.addi %a_ext, %b : i64
    %sub1 = arith.subi %b, %c_ext : i64
    %mul1 = arith.muli %a_ext, %c_ext : i64
    
    // Division and remainder with 64-bit
    %div = arith.divsi %b, %c_ext : i64
    %rem = arith.remsi %b, %c_ext : i64
    
    // Combine results
    %sum1 = arith.addi %add1, %sub1 : i64
    %sum2 = arith.addi %mul1, %div : i64
    %total = arith.addi %sum1, %sum2 : i64
    %result = arith.addi %total, %rem : i64
    
    return %result : i64
  }
}