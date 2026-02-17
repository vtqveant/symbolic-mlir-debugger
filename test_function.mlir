// Test function for debugging - simple conditional
module {
  func.func @test_conditional(%a: i32, %b: i32) -> i32 {
    %c = arith.cmpi slt, %a, %b : i32
    cond_br %c, ^bb1, ^bb2
    
  ^bb1:
    %result1 = arith.addi %a, %b : i32
    br ^bb3(%result1 : i32)
    
  ^bb2:
    %result2 = arith.subi %a, %b : i32
    br ^bb3(%result2 : i32)
    
  ^bb3(%result: i32):
    return %result : i32
  }
}