// Arithmetic operations test for symbolic execution
// Function: compute(i32 %a, i32 %b) -> i32 %result

module {
  func.func @compute(%a: i32, %b: i32) -> i32 {
    %sub = arith.subi %a, %b : i32
    %mul = arith.muli %a, %b : i32
    %div = arith.divsi %a, %b : i32
    %result = arith.addi %sub, %mul : i32
    %final = arith.subi %result, %div : i32
    return %final : i32
  }
}