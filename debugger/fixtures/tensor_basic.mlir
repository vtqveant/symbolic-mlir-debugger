// Basic tensor operations test
module {
  func.func @test_tensor_basic() -> i32 {
    // Create a tensor with splat constant (all elements = 7)
    %c7 = arith.constant 7 : i32
    %tensor = tensor.splat %c7 : tensor<10xi32>
    
    // Extract element at index 2
    %idx = arith.constant 2 : index
    %val1 = tensor.extract %tensor[%idx] : tensor<10xi32>
    
    // Insert new value 42 at index 2, creating new tensor
    %c42 = arith.constant 42 : i32
    %new_tensor = tensor.insert %c42 into %tensor[%idx] : tensor<10xi32>
    
    // Extract from new tensor
    %val2 = tensor.extract %new_tensor[%idx] : tensor<10xi32>
    
    // Return the second extracted value
    return %val2 : i32
  }
}