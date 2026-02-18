// Basic memref operations test
module {
  func.func @test_memref_basic() -> i32 {
    // Allocate a memref with static size
    %mem = memref.alloc() : memref<10xi32>
    
    // Create index constant for array access
    %idx = arith.constant 0 : index
    
    // Store a constant value at index 0
    %c5 = arith.constant 5 : i32
    memref.store %c5, %mem[%idx] : memref<10xi32>
    
    // Load the value back
    %val = memref.load %mem[%idx] : memref<10xi32>
    
    // Return loaded value
    return %val : i32
  }
}