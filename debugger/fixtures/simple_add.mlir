// Simple addition test for symbolic execution
// Function: add(i32 %a, i32 %b) -> i32 %sum

module {
  func.func @add(%a: i32, %b: i32) -> i32 {
    %sum = arith.addi %a, %b : i32
    return %sum : i32
  }
}