"""Parser tests for symbolic MLIR debugger."""

import pytest


@pytest.mark.parser
def test_cmpi_parsing(parser):
    """Test parsing of arith.cmpi with comma syntax."""
    mlir_code = """
module {
  func.func @test(%a: i32, %b: i32) -> i1 {
    %cmp = arith.cmpi slt, %a, %b : i32
    return %cmp : i1
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    assert len(func.basic_blocks) == 1
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    assert bb.operations[0].full_name == "arith.cmpi"
    assert bb.operations[1].full_name == ".return"


@pytest.mark.parser
def test_addi_parsing(parser):
    """Test parsing of arith.addi with comma syntax."""
    mlir_code = """
module {
  func.func @test(%a: i32, %b: i32) -> i32 {
    %sum = arith.addi %a, %b : i32
    return %sum : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    assert bb.operations[0].full_name == "arith.addi"
    assert bb.operations[1].full_name == ".return"


@pytest.mark.parser
def test_negative_constant_parsing(parser):
    """Test parsing of negative constants."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant -42 : i32
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    assert bb.operations[0].full_name == "arith.constant"
    # Check that value is negative
    assert bb.operations[0].value == -42


@pytest.mark.parser
def test_generic_cmpi_parsing(parser):
    """Test parsing of arith.cmpi in generic form (already preprocessed)."""
    mlir_code = """
module {
  func.func @test(%a: i32, %b: i32) -> i1 {
    %cmp = "arith.cmpi"(%a, %b) {predicate = 2 : i64} : (i32, i32) -> i1
    return %cmp : i1
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    assert bb.operations[0].full_name == "arith.cmpi"
    # Should have predicate attribute
    assert "predicate" in str(bb.operations[0].attributes)


# Parameterized test for various arithmetic operations
@pytest.mark.parser
@pytest.mark.parametrize(
    "op,expected_op_name",
    [
        ("addi", "arith.addi"),
        ("subi", "arith.subi"),
        ("muli", "arith.muli"),
        ("divi", "arith.divsi"),
    ],
)
def test_arithmetic_ops_parsing(parser, op, expected_op_name):
    """Test parsing of various arithmetic operations."""
    mlir_code = f"""
module {{
  func.func @test(%a: i32, %b: i32) -> i32 {{
    %result = arith.{op} %a, %b : i32
    return %result : i32
  }}
}}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    assert bb.operations[0].full_name == expected_op_name


# Location parsing tests
@pytest.mark.parser
def test_filelinecol_location_parsing(parser):
    """Test parsing of file:line:col location."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 42 : i32 loc("file.mlir":1:5)
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"
    # Location should be present in operation
    # Note: location parsing may store location in different format
    # For now, just verify parsing succeeds


@pytest.mark.parser
def test_callsite_location_parsing(parser):
    """Test parsing of callsite location."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 42 : i32 loc(callsite("foo" at "bar"))
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"


@pytest.mark.parser
def test_fused_location_parsing(parser):
    """Test parsing of fused location."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 42 : i32 loc(fused["file.mlir":1:2, "file.mlir":3:4])
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"


@pytest.mark.parser
def test_fused_location_with_metadata_parsing(parser):
    """Test parsing of fused location with metadata."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 42 : i32 loc(fused<"metadata">["file.mlir":1:2])
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"


@pytest.mark.parser
def test_name_location_parsing(parser):
    """Test parsing of named location."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 42 : i32 loc("func"("file.mlir":1:2))
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"


@pytest.mark.parser
def test_unknown_location_parsing(parser):
    """Test parsing of unknown location."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 42 : i32 loc(unknown)
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"


# Attribute parsing tests
@pytest.mark.parser
def test_integer_attribute_parsing(parser):
    """Test parsing of integer attribute."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 42 : i32
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"
    assert op.value == 42
    assert op.result_type == "i32"


@pytest.mark.parser
def test_hex_integer_attribute_parsing(parser):
    """Test parsing of hexadecimal integer attribute."""
    mlir_code = """
module {
  func.func @test() -> i32 {
    %c = arith.constant 0x2A : i32
    return %c : i32
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op.full_name == "arith.constant"
    # Value should be parsed as integer 42
    assert op.value == 42  # 0x2A = 42
    assert op.result_type == "i32"


@pytest.mark.parser
def test_string_attribute_parsing(parser):
    """Test parsing of string attribute in generic operation."""
    mlir_code = """
module {
  func.func @test() {
    "foo.op"() {attr = "hello"} : () -> ()
    return
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op["op"] == "foo.op"
    assert "attributes" in op
    # String attribute should be parsed as string "hello"
    assert op["attributes"]["attr"] == "hello"


@pytest.mark.parser
def test_bool_attribute_parsing(parser):
    """Test parsing of boolean attribute."""
    mlir_code = """
module {
  func.func @test() {
    "foo.op"() {flag = true, other = false} : () -> ()
    return
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op["op"] == "foo.op"
    assert "attributes" in op
    # Boolean attributes should be parsed as Python bool
    assert op["attributes"]["flag"] is True
    assert op["attributes"]["other"] is False


@pytest.mark.parser
def test_array_attribute_parsing(parser):
    """Test parsing of array attribute."""
    mlir_code = """
module {
  func.func @test() {
    "foo.op"() {arr = [1, 2, 3]} : () -> ()
    return
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op["op"] == "foo.op"
    assert "attributes" in op
    # Array attribute should be parsed as list
    assert op["attributes"]["arr"] == [1, 2, 3]


@pytest.mark.parser
def test_dictionary_attribute_parsing(parser):
    """Test parsing of dictionary attribute."""
    mlir_code = """
module {
  func.func @test() {
    "foo.op"() {dict = {key1 = 42, key2 = "value"}} : () -> ()
    return
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op["op"] == "foo.op"
    assert "attributes" in op
    # Dictionary attribute should be parsed as dict
    assert op["attributes"]["dict"]["key1"] == 42
    assert op["attributes"]["dict"]["key2"] == "value"


@pytest.mark.parser
def test_cmpi_predicate_attribute_parsing(parser):
    """Test that arith.cmpi predicate attribute is promoted to top-level."""
    mlir_code = """
module {
  func.func @test(%a: i32, %b: i32) -> i1 {
    %cmp = arith.cmpi slt, %a, %b : i32
    return %cmp : i1
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op["op"] == "arith.cmpi"
    # For comma syntax, predicate should be in top-level key
    # (parsed as custom operation, not generic with attributes)
    assert "pred" in op
    assert op["pred"] == "slt"
    # For comma syntax, attributes may not be present
    # Check if attributes exist, then verify pred is also there
    if "attributes" in op:
        assert op["attributes"]["pred"] == "slt"


@pytest.mark.parser
def test_unit_attribute_parsing(parser):
    """Test parsing of unit attribute (no value)."""
    mlir_code = """
module {
  func.func @test() {
    "foo.op"() {unit = unit} : () -> ()
    return
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op["op"] == "foo.op"
    assert "attributes" in op
    # Unit attribute should be parsed as None
    assert op["attributes"]["unit"] is None


@pytest.mark.parser
def test_type_attribute_parsing(parser):
    """Test parsing of type attribute."""
    mlir_code = """
module {
  func.func @test() {
    "foo.op"() {type_attr = i32} : () -> ()
    return
  }
}
"""
    functions = parser.parse_string(mlir_code)
    assert len(functions) == 1
    func = functions["test"]
    bb = list(func.basic_blocks.values())[0]
    assert len(bb.operations) == 2
    op = bb.operations[0]
    assert op["op"] == "foo.op"
    assert "attributes" in op
    # Type attribute should be parsed as type string
    assert op["attributes"]["type_attr"] == "i32"
