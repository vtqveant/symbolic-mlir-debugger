// Arithmetic operations with edge cases
// Function: edge_cases_arith(i32 %a, i32 %b) -> i32 %result

module {
  func.func @edge_cases_arith(%a: i32, %b: i32) -> i32 {
    %zero = arith.constant 0 : i32
    %neg_one = arith.constant -1 : i32
    %max_val = arith.constant 2147483647 : i32  // INT32_MAX
    
    // Handle division by zero case
    %is_zero = arith.cmpi eq, %b, %zero : i32
    %result = scf.if %is_zero -> (i32) {
      // Path 1: division by zero - return special value
      scf.yield %neg_one : i32
    } else {
      // Path 2: normal arithmetic
      %div = arith.divsi %a, %b : i32
      %rem = arith.remsi %a, %b : i32
      
      // Check for overflow in multiplication
      // Check if a is negative
      %is_a_negative = arith.cmpi slt, %a, %zero : i32
      %abs_a = scf.if %is_a_negative -> (i32) {
        %neg_a = arith.subi %zero, %a : i32
        scf.yield %neg_a : i32
      } else {
        scf.yield %a : i32
      }
      
      %cmp_overflow = arith.cmpi sgt, %abs_a, %max_val : i32
      %result2 = scf.if %cmp_overflow -> (i32) {
        // Potential overflow path
        %mul = arith.muli %a, %neg_one : i32  // Safe multiplication
        %result3 = arith.addi %div, %mul : i32
        %final = arith.addi %result3, %rem : i32
        scf.yield %final : i32
      } else {
        // Normal multiplication
        %mul = arith.muli %a, %b : i32
        %result4 = arith.addi %div, %mul : i32
        %final = arith.addi %result4, %rem : i32
        scf.yield %final : i32
      }
      scf.yield %result2 : i32
    }
    
    return %result : i32
  }
}