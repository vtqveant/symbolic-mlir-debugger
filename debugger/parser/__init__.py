"""
MLIR parser package (pymlir fork).
"""

from . import astnodes as astnodes
from . import dialect as dialect
from . import parser as parser
from . import parser_transformer as parser_transformer
from . import visitors as visitors
from .dialects import *
from .parser import parse_string, parse_file
