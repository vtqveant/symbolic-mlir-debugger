// Concrete loop test for symbolic execution
// Function: sum_5() -> i32 %sum
// Computes sum of integers from 0 to 4 using scf.for

module {
  func.func @sum_5() -> i32 {
    %c0 = arith.constant 0 : index
    %c1 = arith.constant 1 : index
    %c5 = arith.constant 5 : index
    %sum_init = arith.constant 0 : i32
    
    %result = scf.for %i = %c0 to %c5 step %c1 iter_args(%sum_iter = %sum_init) -> i32 {
      %i_i32 = arith.index_cast %i : index to i32
      %sum_next = arith.addi %sum_iter, %i_i32 : i32
      scf.yield %sum_next : i32
    }
    
    return %result : i32
  }
}