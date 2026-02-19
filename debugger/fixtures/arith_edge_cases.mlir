// Arithmetic operations with edge cases
// Function: edge_cases_arith(i32 %a, i32 %b) -> i32 %result

module {
  func.func @edge_cases_arith(%a: i32, %b: i32) -> i32 {
    %zero = arith.constant 0 : i32
    %neg_one = arith.constant -1 : i32
    %max_val = arith.constant 2147483647 : i32  // INT32_MAX
    %min_val = arith.constant -2147483648 : i32 // INT32_MIN
    
    // Handle division by zero case
    %is_zero = arith.cmpi eq, %b, %zero : i32
    scf.if %is_zero {
      // Path 1: division by zero - return special value
      scf.yield %neg_one : i32
    } else {
      // Path 2: normal arithmetic
      %div = arith.divsi %a, %b : i32
      %rem = arith.remsi %a, %b : i32
      
      // Check for overflow in multiplication
      %abs_a = arith.abs %a : i32
      %abs_b = arith.abs %b : i32
      %cmp_overflow = arith.cmpi sgt, %abs_a, %max_val : i32
      scf.if %cmp_overflow {
        // Potential overflow path
        %mul = arith.muli %a, %neg_one : i32  // Safe multiplication
        %result = arith.addi %div, %mul : i32
        %final = arith.addi %result, %rem : i32
        scf.yield %final : i32
      } else {
        // Normal multiplication
        %mul = arith.muli %a, %b : i32
        %result = arith.addi %div, %mul : i32
        %final = arith.addi %result, %rem : i32
        scf.yield %final : i32
      }
    }
  }
}