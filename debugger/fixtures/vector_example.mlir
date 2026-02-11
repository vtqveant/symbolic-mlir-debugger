// Vector dialect example
func.func @vector_ops(%arg0: f32, %arg1: f32) -> (i32, i32, i32) {
  // vector.broadcast broadcasts scalar to vector
  %vec1 = vector.broadcast %arg0 : f32 to vector<4xf32>
  
  // vector.bitcast changes vector element type (to integer for demonstration)
  %vec2 = vector.bitcast %vec1 : vector<4xf32> to vector<2xi64>
  
  // vector.fma: fused multiply-add (using generic syntax)
  %vec_a = vector.broadcast %arg0 : f32 to vector<4xf32>
  %vec_b = vector.broadcast %arg1 : f32 to vector<4xf32>
  %vec_c = vector.broadcast %arg0 : f32 to vector<4xf32>
  %vec_fma = "vector.fma"(%vec_a, %vec_b, %vec_c) : (vector<4xf32>, vector<4xf32>, vector<4xf32>) -> vector<4xf32>
  
  // Return some values
  %c42 = arith.constant 42 : i32
  %c100 = arith.constant 100 : i32
  %c1 = arith.constant 1 : i32
  
  return %c42, %c100, %c1 : i32, i32, i32
}