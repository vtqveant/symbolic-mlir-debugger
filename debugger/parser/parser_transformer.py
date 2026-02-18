from lark import Transformer
from lark.visitors import v_args

from . import astnodes


class TreeToMlir(Transformer):
    ###############################################################
    # Low-level literal syntax
    digit = lambda self, val: int(val[0])
    digits = lambda self, val: int(val[0])
    hex_digit = lambda self, val: str(val[0])
    hex_digits = lambda self, val: str(val[0])
    letter = lambda self, val: str(val[0])
    letters = lambda self, val: str(val[0])
    id_punct = lambda self, val: str(val[0])
    underscore = lambda self, val: str(val[0])
    true = lambda self, _: True
    false = lambda self, _: False
    id_chars = lambda self, val: str(val[0])
    inttype_width = lambda self, val: int(val[0])
    dimension = astnodes.Dimension.from_lark

    # Literals
    @v_args(inline=True)
    def decimal_literal(self, *digits):
        return int("".join(str(d) for d in digits))

    @v_args(inline=True)
    def hexadecimal_literal(self, *digits):
        return int("".join(digits), 16)

    negated_integer_literal = lambda self, value: -value[0]
    float_literal = lambda self, value: float(value[0])

    @v_args(inline=True)
    def string_literal(self, s):
        return astnodes.StringLiteral(s[1:-1].replace('\\"', '"'))

    @v_args(inline=True)
    def bare_id(self, *elements):
        return "".join(str(s) for s in elements)

    @v_args(inline=True)
    def suffix_id(self, *suffix):
        return "".join(str(s) for s in suffix)

    ###############################################################
    # MLIR Identifiers

    ssa_id = astnodes.SsaId.from_lark
    symbol_ref_id = astnodes.SymbolRefId.from_lark
    block_id = astnodes.BlockId.from_lark
    type_alias = astnodes.TypeAlias.from_lark
    attribute_alias = astnodes.AttrAlias.from_lark
    map_or_set_id = astnodes.MapOrSetId.from_lark

    ###############################################################
    # MLIR Types

    none_type = astnodes.NoneType.from_lark
    F16 = lambda self, tok: astnodes.FloatTypeEnum("f16")
    BF16 = lambda self, tok: astnodes.FloatTypeEnum("bf16")
    F32 = lambda self, tok: astnodes.FloatTypeEnum("f32")
    F64 = lambda self, tok: astnodes.FloatTypeEnum("f64")
    float_type = lambda self, tok: astnodes.FloatType(astnodes.FloatTypeEnum(tok[0].value))
    index_type = astnodes.IndexType.from_lark
    signed_integer_type = lambda self, tok: astnodes.SignedIntegerType(int(tok[0].value[2:]))
    unsigned_integer_type = lambda self, tok: astnodes.UnsignedIntegerType(int(tok[0].value[2:]))
    signless_integer_type = lambda self, tok: astnodes.SignlessIntegerType(int(tok[0].value[1:]))
    complex_type = astnodes.ComplexType.from_lark
    tuple_type = astnodes.TupleType.from_lark
    vector_type = astnodes.VectorType.from_lark
    ranked_tensor_type = astnodes.RankedTensorType.from_lark
    unranked_tensor_type = lambda self, value: astnodes.UnrankedTensorType(
        value[1]
    )  # gets rid of literal "*x"
    ranked_memref_type = astnodes.RankedMemRefType.from_lark
    unranked_memref_type = astnodes.UnrankedMemRefType.from_lark
    opaque_dialect_item = astnodes.OpaqueDialectType.from_lark

    @v_args(inline=True)
    def pretty_dialect_item(self, *args):
        # args: could be (dialect, type_name) or (dialect, dot, type_name) with optional body
        # dot is ignored if present
        if len(args) == 2:
            # No dot token: (dialect, type_name)
            dialect, type_name = args
        elif len(args) >= 3 and args[1] == ".":
            # Has dot token: (dialect, '.', type_name, ...)
            dialect, dot, type_name = args[0], args[1], args[2]
            args = args[3:]
        elif len(args) >= 3:
            # Assume first two are dialect and type_name, third might be body
            dialect, type_name = args[0], args[1]
            args = args[2:]
        else:
            raise ValueError(f"Unexpected args for pretty_dialect_item: {args}")

        body_items = []
        if args:
            # Remaining args are body
            body_items = args[0]  # body is a list
        return astnodes.PrettyDialectType(dialect, type_name, body_items)

    llvm_function_type = astnodes.LlvmFunctionType.from_lark
    function_type = astnodes.FunctionType.from_lark
    strided_layout = astnodes.StridedLayout.from_lark

    ###############################################################
    # MLIR Attributes

    array_attribute = astnodes.ArrayAttr
    bool_attribute = astnodes.BoolAttr.from_lark
    dictionary_attribute = astnodes.DictionaryAttr
    dense_elements_attribute = astnodes.DenseElementsAttr.from_lark
    opaque_elements_attribute = astnodes.OpaqueElementsAttr.from_lark
    sparse_elements_attribute = astnodes.SparseElementsAttr.from_lark
    float_attribute = astnodes.FloatAttr.from_lark
    integer_attribute = astnodes.IntegerAttr.from_lark
    integer_set_attribute = astnodes.IntSetAttr.from_lark
    string_attribute = astnodes.StringAttr.from_lark
    symbol_ref_attribute = astnodes.SymbolRefAttr
    type_attribute = astnodes.TypeAttr.from_lark
    unit_attribute = astnodes.UnitAttr.from_lark

    dependent_attribute_entry = astnodes.AttributeEntry.from_lark
    dialect_attribute_entry = astnodes.DialectAttributeEntry.from_lark
    attribute_dict = astnodes.AttributeDict
    fusion_metadata = lambda self, value: value[0]

    ###############################################################
    # Operations

    op_result = astnodes.OpResult.from_lark

    def location(self, value):
        child = value[0]
        if isinstance(child, astnodes.StringLiteral):
            return astnodes.StrLocation(child.value)
        # Otherwise child is already a Location object (from sub-rules)
        return child

    @v_args(inline=True)
    def filelinecol_location(self, file, line, col, *args):
        # args: optional "to" token, end_line, end_col (if present)
        end_line = None
        end_col = None
        if len(args) == 3:
            # args[0] is "to" token (ignored), args[1] end_line, args[2] end_col
            end_line = args[1]
            end_col = args[2]
        # Note: file is StringLiteral, need to extract string
        return astnodes.FileLineColLoc(file.value, line, col, end_line, end_col)

    callsite_location = astnodes.CallSiteLoc.from_lark

    @v_args(inline=True)
    def fused_location(self, *args):
        # args: optional metadata (Attribute), then list of locations
        # The grammar: fused metadata? '[' (location (',' location)*)? ']'
        # Lark flattens: metadata (if present) followed by locations
        # We need to detect if first arg is metadata (Attribute) or location
        metadata = None
        locations = []
        for arg in args:
            if isinstance(arg, astnodes.Attribute):
                metadata = arg
            else:
                locations.append(arg)
        return astnodes.FusedLoc(locations, metadata)

    @v_args(inline=True)
    def name_location(self, name, *args):
        # args: optional child location (0 or 1 element)
        child = args[0] if args else None
        # name is StringLiteral
        return astnodes.NameLoc(name.value, child)

    unknown_location = astnodes.UnknownLoc.from_lark

    operation = astnodes.Operation.from_lark
    generic_operation = astnodes.GenericOperation.from_lark
    custom_operation = astnodes.CustomOperation.from_lark

    ###############################################################
    # Blocks, regions, modules, functions

    def block_label(self, value):
        if value[1] is None:
            arg_ids, argtypes = None, None
        else:
            # value[1] is a list of (SsaId, Type) pairs
            arg_ids = [pair[0] for pair in value[1]]
            argtypes = [pair[1] for pair in value[1]]
        return astnodes.BlockLabel(value[0], arg_ids, argtypes)

    block = astnodes.Block.from_lark

    def region(self, blocks):
        """Parse a region, merging labeled blocks with anonymous single-operation successors.

        pymlir has a bug where labeled blocks with terminators are split into two blocks:
        a labeled block with non-terminator operations and an anonymous block with only
        the terminator. This method merges such anonymous blocks back into the preceding
        labeled block to ensure each labeled block contains its terminator.
        """
        if not blocks:
            return astnodes.Region([])
        merged = []
        i = 0
        while i < len(blocks):
            block = blocks[i]
            # Check if this block has a label (i.e., not synthetic)
            has_label = block.label and block.label.name
            # Check if next block exists and is anonymous (no label)
            if (
                i + 1 < len(blocks)
                and has_label
                and not blocks[i + 1].label
                and len(blocks[i + 1].body) == 1
            ):
                next_block = blocks[i + 1]
                # Merge: append operation to current block's body
                block.body.append(next_block.body[0])
                merged.append(block)
                i += 2  # skip next block
                continue
            merged.append(block)
            i += 1
        return astnodes.Region(merged)

    module = astnodes.Module.from_lark
    function = astnodes.Function.from_lark
    generic_module = astnodes.GenericModule.from_lark
    named_argument = astnodes.NamedArgument.from_lark
    argument_assignment = astnodes.ArgumentAssignment.from_lark

    ###############################################################
    # (semi-)Affine expressions, maps, and integer sets

    dim_and_symbol_id_lists = astnodes.DimAndSymbolList.from_lark
    dim_and_symbol_use_list = astnodes.DimAndSymbolList.from_lark

    affine_expr = astnodes.AffineExpr.from_lark
    semi_affine_expr = astnodes.SemiAffineExpr.from_lark
    multi_dim_affine_expr = astnodes.MultiDimAffineExpr.from_lark
    multi_dim_semi_affine_expr = astnodes.MultiDimSemiAffineExpr.from_lark

    affine_constraint_ge = astnodes.AffineConstraintGreaterEqual.from_lark
    affine_constraint_eq = astnodes.AffineConstraintEqual.from_lark

    affine_map_inline = astnodes.AffineMap.from_lark
    semi_affine_map_inline = astnodes.SemiAffineMap.from_lark
    integer_set_inline = astnodes.IntSet.from_lark

    affine_neg = astnodes.AffineNeg.from_lark
    semi_affine_neg = astnodes.AffineNeg.from_lark
    affine_parens = astnodes.AffineParens.from_lark
    semi_affine_parens = astnodes.AffineParens.from_lark
    affine_symbol_explicit = astnodes.AffineExplicitSymbol.from_lark
    semi_affine_symbol_explicit = astnodes.AffineExplicitSymbol.from_lark
    affine_add = astnodes.AffineAdd.from_lark
    semi_affine_add = astnodes.AffineAdd.from_lark
    affine_sub = astnodes.AffineSub.from_lark
    semi_affine_sub = astnodes.AffineSub.from_lark
    affine_mul = astnodes.AffineMul.from_lark
    semi_affine_mul = astnodes.AffineMul.from_lark
    affine_floordiv = astnodes.AffineFloorDiv.from_lark
    semi_affine_floordiv = astnodes.AffineFloorDiv.from_lark
    affine_ceildiv = astnodes.AffineCeilDiv.from_lark
    semi_affine_ceildiv = astnodes.AffineCeilDiv.from_lark
    affine_mod = astnodes.AffineMod.from_lark
    semi_affine_mod = astnodes.AffineMod.from_lark

    ###############################################################
    # Top-level definitions

    type_alias_def = astnodes.TypeAliasDef.from_lark
    affine_map_def = astnodes.AffineMapDef.from_lark
    semi_affine_map_def = astnodes.SemiAffineMapDef.from_lark
    integer_set_def = astnodes.IntSetDef.from_lark
    attribute_alias_def = astnodes.AttrAliasDef.from_lark

    ###############################################################
    # List types
    bare_id_list = list
    ssa_id_list = list
    ssa_use_list = list
    op_result_list = list
    successor_list = list

    @v_args(inline=True)
    def optional_paren_ssa_use_list(self, *args):
        # Handle two cases:
        # 1. "(" optional_ssa_use_list ")" -> args = ['(', ssa_use_list, ')']
        # 2. optional_ssa_use_list -> args = [ssa_use_list] or []
        if len(args) == 3 and args[0] == "(" and args[2] == ")":
            # Case 1: with parentheses
            return args[1]  # Return the ssa_use_list
        elif len(args) == 1:
            # Case 2: without parentheses, with ssa_use_list
            return args[0]
        elif len(args) == 0:
            # Case 2: without parentheses, empty ssa_use_list
            return []
        else:
            # Unexpected case
            raise ValueError(f"Unexpected args for optional_paren_ssa_use_list: {args}")

    ssa_id_and_type = tuple
    ssa_id_and_type_list = tuple
    ssa_use_and_type_list = list
    stride_list = list
    dimension_list_ranked = list
    static_dimension_list = list
    pretty_dialect_item_body = list
    type_list_no_parens = list
    affine_constraint_conjunction = list
    function_result_list_no_parens = list
    multi_dim_affine_expr_no_parens = list
    multi_dim_semi_affine_expr_no_parens = list
    dim_id_list = list
    symbol_id_list = list
    dim_use_list = list
    symbol_use_list = list
    operation_list = list
    argument_list = list
    argument_assignment_list_no_parens = list
    definition_list = list
    function_list = list
    module_list = list
    block_arg_list = list
    definition_and_function_list = tuple
    definition_and_module_list = tuple
    region_list = list

    ###############################################################
    # Composite types that should be reduced to sub-types
    bool_literal = lambda self, value: value[0]
    integer_literal = lambda self, value: value[0]
    constant_literal = lambda self, value: value[0]
    dimension_list = lambda self, value: value[0]
    ssa_use = lambda self, value: value[0]
    integer_type = lambda self, value: value[0]
    vector_element_type = lambda self, value: value[0]
    tensor_memref_element_type = lambda self, value: value[0]
    tensor_type = lambda self, value: value[0]
    memref_type = lambda self, value: value[0]
    standard_type = lambda self, value: value[0]
    dialect_type = lambda self, value: value[0]
    non_function_type = lambda self, value: value[0]
    type = lambda self, value: value[0]
    type_list_parens = lambda self, value: (value[0] if value else [])
    function_result = lambda self, value: value[0]
    function_result_type = lambda self, value: value[0]
    standard_attribute = lambda self, value: value[0]
    attribute_value = lambda self, value: value[0]
    dialect_attribute = lambda self, value: value[0]
    attribute_entry = lambda self, value: value[0]
    trailing_type = lambda self, value: value[0]
    trailing_location = lambda self, value: value[0]
    function_result_list_parens = lambda self, value: (value[0] if value else [])
    symbol_or_const = lambda self, value: value[0]
    affine_map = lambda self, value: value[0]
    semi_affine_map = lambda self, value: value[0]
    integer_set = lambda self, value: value[0]
    affine_literal = lambda self, value: value[0]
    semi_affine_literal = lambda self, value: value[0]
    affine_ssa = lambda self, value: astnodes.AffineSsa(value[0].value, value[0].op_no)
    affine_dim_or_symbol = astnodes.AffineDimOrSymbol.from_lark
    semi_affine_symbol = lambda self, value: value[0]

    ###############################################################
    # MLIR file

    def only_functions_and_definitions_file(self, defns_and_fns):
        assert isinstance(defns_and_fns, list)
        assert all(isinstance(el, tuple) for el in defns_and_fns)
        defns = sum([defns for defns, fns in defns_and_fns], [])
        fns = sum([fns for defns, fns in defns_and_fns], [])
        if len(fns) == 0:
            return astnodes.MLIRFile(defns, [])
        else:
            fns = [astnodes.Operation([], fn) for fn in fns]
            return astnodes.MLIRFile(
                defns,
                [astnodes.Module(None, None, astnodes.Region([astnodes.Block(None, fns)]))],
            )

    def mlir_file_as_definition_and_module_list(self, defns_and_mods):
        assert isinstance(defns_and_mods, list)
        assert all(isinstance(el, tuple) for el in defns_and_mods)
        defns = sum([defns for defns, mods in defns_and_mods], [])
        mods = sum([mods for defns, mods in defns_and_mods], [])
        return astnodes.MLIRFile(defns, mods)

    # Dialect ops and types are appended to this list via "setattr"

    def optional(self, value):
        assert isinstance(value, list)
        assert len(value) in [0, 1]
        return value[0] if value else None
