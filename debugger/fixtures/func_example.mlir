// Func dialect examples for symbolic execution
module {
  // Simple function call
  func.func @add(%a: i32, %b: i32) -> i32 {
    %sum = arith.addi %a, %b : i32
    return %sum : i32
  }

  func.func @caller(%x: i32, %y: i32) -> i32 {
    %result = func.call @add(%x, %y) : (i32, i32) -> i32
    return %result : i32
  }

  // Multiple returns - disabled due to cf.cond_br parsing issue
  // func.func @max(%a: i32, %b: i32) -> i32 {
  //   %cmp = arith.cmpi sgt, %a, %b : i32
  //   cf.cond_br %cmp, ^true, ^false
  //   
  // ^true:
  //   return %a : i32
  //   
  // ^false:
  //   return %b : i32
  // }

  // Function with memref argument
  func.func @process_buffer(%buf: memref<10xi32>) -> i32 {
    %c0_index = arith.constant 0 : index
    %c1_i32 = arith.constant 1 : i32
    %first = affine.load %buf[%c0_index] : memref<10xi32>
    %result = arith.addi %first, %c1_i32 : i32
    return %result : i32
  }
}