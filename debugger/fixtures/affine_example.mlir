// Affine dialect examples for symbolic execution
module {
  // #set0 = affine_set<(d0) : (d0 >= 0)>
  // Simple affine.for loop
  func.func @affine_for_example(%lb: index, %ub: index) -> index {
    %c0 = arith.constant 0 : index
    %sum = arith.constant 0 : index
    affine.for %i = %lb to %ub {
      %sum_next = arith.addi %sum, %i : index
      // Store updated sum (in real MLIR we'd use SSA, this is simplified)
    }
    return %sum : index
  }

  // Affine.if with condition (disabled due to LSP parsing issue)
  // func.func @affine_if_example(%A: memref<10xi32>, %idx: index) -> i32 {
  //   %c5 = arith.constant 5 : index
  //   %cond = arith.cmpi slt, %idx, %c5 : index
  //   affine.if #set0 (%idx) {
  //     %val = affine.load %A[%idx] : memref<10xi32>
  //     return %val : i32
  //   } else {
  //     %c0 = arith.constant 0 : i32
  //     return %c0 : i32
  //   }
  // }

  // Affine load/store
  func.func @affine_memref_example(%A: memref<10x10xi32>, %i: index, %j: index) -> i32 {
    %c1 = arith.constant 1 : i32
    affine.store %c1, %A[%i, %j] : memref<10x10xi32>
    %val = affine.load %A[%i, %j] : memref<10x10xi32>
    return %val : i32
  }
}