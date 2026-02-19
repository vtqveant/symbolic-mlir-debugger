// Arithmetic operations with conditional branches
// Function: conditional_arith(i32 %a, i32 %b) -> i32 %result

module {
  func.func @conditional_arith(%a: i32, %b: i32) -> i32 {
    %zero = arith.constant 0 : i32
    %one = arith.constant 1 : i32
    
    // Check if a > b
    %cmp_gt = arith.cmpi sgt, %a, %b : i32
    %result = scf.if %cmp_gt -> (i32) {
      // Path 1: a > b
      %diff = arith.subi %a, %b : i32
      %result1 = arith.muli %diff, %one : i32
      scf.yield %result1 : i32
    } else {
      // Check if a < b
      %cmp_lt = arith.cmpi slt, %a, %b : i32
      %result2 = scf.if %cmp_lt -> (i32) {
        // Path 2: a < b
        %sum = arith.addi %a, %b : i32
        %result3 = arith.divsi %sum, %one : i32
        scf.yield %result3 : i32
      } else {
        // Path 3: a == b
        %result4 = arith.muli %a, %b : i32
        scf.yield %result4 : i32
      }
      scf.yield %result2 : i32
    }
    
    return %result : i32
  }
}