// EmitC dialect example with LSP-compatible syntax
func.func @emitc_ops(%arg0: i32, %arg1: i32) -> (i32, i32, i1) {
  // emitc.constant creates a constant (generic syntax)
  %const = "emitc.constant"() {value = 42 : i32} : () -> i32
  
  // emitc.add adds two values (generic syntax)
  %sum = "emitc.add"(%arg0, %arg1) : (i32, i32) -> i32
  
  // emitc.cmp compares two values (predicate integer: 5 = slt, 0 = eq)
  %cmp = "emitc.cmp"(%arg0, %arg1) {predicate = 5 : i64} : (i32, i32) -> i1
  
  // emitc.conditional selects value based on condition
  %cond = "emitc.cmp"(%arg0, %arg1) {predicate = 0 : i64} : (i32, i32) -> i1
  %sel = "emitc.conditional"(%cond, %arg0, %arg1) : (i1, i32, i32) -> i32
  
  // emitc.cast casts between types (generic syntax)
  %cast = "emitc.cast"(%arg0) : (i32) -> i64
  
  // Return some values
  return %const, %sum, %cmp : i32, i32, i1
}