// Conditional branch test for symbolic execution
// Function: max(i32 %a, i32 %b) -> i32 %max

module {
  func.func @max(%a: i32, %b: i32) -> i32 {
    %cond = arith.cmpi slt, %a, %b : i32
    cf.cond_br %cond, ^bb1, ^bb2
    
  ^bb1:  // a < b
    return %b : i32
    
  ^bb2:  // a >= b
    return %a : i32
  }
}