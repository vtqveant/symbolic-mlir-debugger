// Simple loop test for symbolic execution
// Function: sum_first_n(i32 %n) -> i32 %total
// Computes sum of integers from 1 to n
// Using scf.for which is simpler and more compatible

module {
  func.func @sum_first_n(%n: i32) -> i32 {
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %c1_i32 = arith.constant 1 : i32
    %total_init = arith.constant 0 : i32
    
    // Convert n to index for loop
    %n_index = arith.index_cast %n : i32 to index
    
    %result = scf.for %i = %c0 to %n_index step %c1 iter_args(%total_iter = %total_init) -> i32 {
      %i_i32 = arith.index_cast %i : index to i32
      %i_plus_one = arith.addi %i_i32, %c1_i32 : i32
      %total_next = arith.addi %total_iter, %i_plus_one : i32
      scf.yield %total_next : i32
    }
    
    return %result : i32
  }
}