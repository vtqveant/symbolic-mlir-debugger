// Affine for loop with iter_args test for symbolic execution
// Function: sum_affine_loop(i32 %n) -> i32 %sum
// Computes sum of integers from 0 to n-1 using affine.for

module {
  func.func @sum_affine_loop(%n: i32) -> i32 {
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %sum_init = arith.constant 0 : i32
    %n_index = arith.index_cast %n : i32 to index
    
    %result = affine.for %i = %c0 to %n_index step %c1 iter_args(%sum_iter = %sum_init) -> i32 {
      %i_i32 = arith.index_cast %i : index to i32
      %sum_next = arith.addi %sum_iter, %i_i32 : i32
      affine.yield %sum_next : i32
    }
    
    return %result : i32
  }
}