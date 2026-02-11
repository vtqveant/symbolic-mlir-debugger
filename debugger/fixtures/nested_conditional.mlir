// Nested conditional test for symbolic execution
// Function: max3(i32 %a, i32 %b, i32 %c) -> i32 %max

module {
  func.func @max3(%a: i32, %b: i32, %c: i32) -> i32 {
    %cond1 = arith.cmpi slt, %a, %b : i32
    cf.cond_br %cond1, ^bb1, ^bb2

  ^bb1:  // a < b
    %cond2 = arith.cmpi slt, %b, %c : i32
    cf.cond_br %cond2, ^bb3, ^bb4

  ^bb3:  // b < c
    return %c : i32

  ^bb4:  // b >= c
    return %b : i32

  ^bb2:  // a >= b
    %cond3 = arith.cmpi slt, %a, %c : i32
    cf.cond_br %cond3, ^bb5, ^bb6

  ^bb5:  // a < c
    return %c : i32

  ^bb6:  // a >= c
    return %a : i32
  }
}