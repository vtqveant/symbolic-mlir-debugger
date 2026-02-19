// Arithmetic operations with conditional branches
// Function: conditional_arith(i32 %a, i32 %b) -> i32 %result

module {
  func.func @conditional_arith(%a: i32, %b: i32) -> i32 {
    %zero = arith.constant 0 : i32
    %one = arith.constant 1 : i32
    
    // Check if a > b
    %cmp_gt = arith.cmpi sgt, %a, %b : i32
    scf.if %cmp_gt {
      // Path 1: a > b
      %diff = arith.subi %a, %b : i32
      %result = arith.muli %diff, %one : i32
      scf.yield %result : i32
    } else {
      // Check if a < b
      %cmp_lt = arith.cmpi slt, %a, %b : i32
      scf.if %cmp_lt {
        // Path 2: a < b
        %sum = arith.addi %a, %b : i32
        %result = arith.divsi %sum, %one : i32
        scf.yield %result : i32
      } else {
        // Path 3: a == b
        %result = arith.muli %a, %b : i32
        scf.yield %result : i32
      }
    }
  }
}