// Shape dialect example with LSP-compatible syntax
module {
  func.func @shape_ops() -> (!shape.size, !shape.size, !shape.size, !shape.shape, !shape.size) {
    // shape.const_size creates a shape dimension size
    %size1 = "shape.const_size"() {value = 42 : index} : () -> !shape.size
    %size2 = "shape.const_size"() {value = 100 : index} : () -> !shape.size
    %size3 = "shape.const_size"() {value = 200 : index} : () -> !shape.size
    
    // shape.add adds two shape dimensions
    %sum = "shape.add"(%size1, %size2) : (!shape.size, !shape.size) -> !shape.size
    
    // shape.div divides two shape dimensions  
    %div = "shape.div"(%size2, %size1) : (!shape.size, !shape.size) -> !shape.size
    
    // shape.const_shape creates a shape from dimension sizes
    %shape_val = "shape.const_shape"() {shape = dense<[42, 100, 200]> : tensor<3xindex>} : () -> !shape.shape
    
    // shape.get_extent extracts dimension from shape
    %c0 = arith.constant 0 : index
    %dim0 = "shape.get_extent"(%shape_val, %c0) : (!shape.shape, index) -> !shape.size
    
    // Return values
    return %size1, %sum, %div, %shape_val, %dim0 : !shape.size, !shape.size, !shape.size, !shape.shape, !shape.size
  }
}