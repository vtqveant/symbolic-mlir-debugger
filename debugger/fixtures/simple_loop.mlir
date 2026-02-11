// Simple loop test for symbolic execution
// Function: sum_first_n(i32 %n) -> i32 %total
// Computes sum of integers from 1 to n

module {
  func.func @sum_first_n(%n: i32) -> i32 {
    %c0 = arith.constant 0 : i32
    %c1 = arith.constant 1 : i32
    %i = arith.constant 0 : i32
    %total = arith.constant 0 : i32
    
    // Start loop
    cf.br ^loop_header(%i : i32, %total : i32)
    
  ^loop_header(%i_val: i32, %total_val: i32):
    %cond = arith.cmpi slt, %i_val, %n : i32
    cf.cond_br %cond, ^loop_body, ^loop_exit
    
  ^loop_body:
    %i_next = arith.addi %i_val, %c1 : i32
    %total_next = arith.addi %total_val, %i_next : i32
    cf.br ^loop_header(%i_next : i32, %total_next : i32)
    
  ^loop_exit:
    return %total_val : i32
  }
}