// Linalg dialect examples for symbolic execution
module {
  // Simple linalg.generic operation (simplified)
  func.func @linalg_generic_example(%A: memref<10x10xf32>, %B: memref<10x10xf32>) {
    // C = A + B
    linalg.generic {
        indexing_maps = [affine_map<(i, j) -> (i, j)>, 
                         affine_map<(i, j) -> (i, j)>, 
                         affine_map<(i, j) -> (i, j)>],
        iterator_types = ["parallel", "parallel"]
    } ins(%A, %B : memref<10x10xf32>, memref<10x10xf32>)
      outs(%A : memref<10x10xf32>) {
      ^bb0(%a: f32, %b: f32, %c: f32):
        %sum = arith.addf %a, %b : f32
        linalg.yield %sum : f32
    }
    return
  }

  // Matrix multiplication
  func.func @matmul(%A: memref<100x100xf32>, %B: memref<100x100xf32>, %C: memref<100x100xf32>) {
    linalg.matmul ins(%A, %B : memref<100x100xf32>, memref<100x100xf32>)
                 outs(%C : memref<100x100xf32>)
    return
  }

  // Batch matrix multiplication
  func.func @batch_matmul(%A: memref<10x100x100xf32>, %B: memref<10x100x100xf32>, %C: memref<10x100x100xf32>) {
    linalg.batch_matmul ins(%A, %B : memref<10x100x100xf32>, memref<10x100x100xf32>)
                       outs(%C : memref<10x100x100xf32>)
    return
  }
}