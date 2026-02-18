// Bufferization dialect example with LSP-compatible syntax
module {
  func.func @bufferization_ops() -> (i32, i32) {
    // bufferization.alloc_tensor allocates a tensor with static size
    %tensor = "bufferization.alloc_tensor"() : () -> tensor<10x20xi32>
    
    // bufferization.to_memref converts tensor to memref (using generic syntax)
    %memref = "bufferization.to_memref"(%tensor) : (tensor<10x20xi32>) -> memref<10x20xi32>
    
    // bufferization.clone creates a copy of memref
    %memref_clone = "bufferization.clone"(%memref) : (memref<10x20xi32>) -> memref<10x20xi32>
    
    // bufferization.to_tensor converts memref back to tensor (using generic syntax)
    %tensor2 = "bufferization.to_tensor"(%memref_clone) : (memref<10x20xi32>) -> tensor<10x20xi32>
    
    // Return some values
    %c42 = arith.constant 42 : i32
    %c100 = arith.constant 100 : i32
    
    return %c42, %c100 : i32, i32
  }
}