"""
MLIR parser package (pymlir fork).
"""

from . import parser_transformer
from . import astnodes
from . import parser
from . import dialect
from . import visitors
from .parser import parse_string, parse_file
from .dialects import *
