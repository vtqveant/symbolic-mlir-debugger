// Basic arithmetic operations test for symbolic execution
// Function: basic_arith(i32 %a, i32 %b) -> i32 %result

module {
  func.func @basic_arith(%a: i32, %b: i32) -> i32 {
    // Test all basic arithmetic operations
    %add = arith.addi %a, %b : i32
    %sub = arith.subi %a, %b : i32
    %mul = arith.muli %a, %b : i32
    %div = arith.divsi %a, %b : i32
    %rem = arith.remsi %a, %b : i32
    
    // Combine results
    %sum1 = arith.addi %add, %sub : i32
    %sum2 = arith.addi %mul, %div : i32
    %total = arith.addi %sum1, %sum2 : i32
    %result = arith.addi %total, %rem : i32
    
    return %result : i32
  }
}