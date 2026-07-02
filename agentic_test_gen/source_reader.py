"""Source reader — read the target file and find the functions to test.

We use Python's built-in `ast` (Abstract Syntax Tree) module to *parse* the code
into a structured tree, rather than guessing with string search. From that tree
we pull out the function names, which we'll hand to the model so it knows exactly
what to cover (grounding the prompt in real facts = better, less 'made up' output).
"""

import ast
from pathlib import Path

from .models import SourceInfo


def read_source(path: str) -> SourceInfo:
    code = Path(path).read_text()

    # Parse the source text into an AST (a tree of nodes describing the code).
    tree = ast.parse(code)

    # Walk every node in the tree and keep the ones that are function definitions.
    function_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]

    return SourceInfo(
        module_name=Path(path).stem,   # "calculator.py" -> "calculator"
        path=path,
        code=code,
        function_names=function_names,
    )
