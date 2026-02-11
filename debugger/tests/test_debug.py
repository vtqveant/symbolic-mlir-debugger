import pytest
import parser.astnodes as mast
import parser


def test_debug():
    code = """
module {
  func.func @test() -> i32 {
     %c = arith.constant 42 : i32
    cf.br ^exit

  ^exit:
    return %c : i32
  }
}
"""
    ast = parser.parse_string(code)
    for module in ast.modules:
        print(f"Module: {module}")
        region = module.region
        print(f"Region: {region}")
        print(f"Region body length: {len(region.body)}")
        for i, block in enumerate(region.body):
            print(f"Block {i}: {block}")
            print(f"  label attr: {block.label}")
            if block.label:
                print(f"  label.name: {block.label.name}")
                print(f"  label.name.value: {block.label.name.value}")
            # check if there is a mapping from label to block
        # check region attributes
        print("Region dir:", [a for a in dir(region) if not a.startswith("_")])
        if hasattr(region, "blocks"):
            print(f"region.blocks: {region.blocks}")
        if hasattr(region, "symbol_table"):
            print(f"symbol_table: {region.symbol_table}")
        # Check if region has a dict mapping label to block index
        break
