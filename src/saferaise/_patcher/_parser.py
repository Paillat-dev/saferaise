"""
Implements functionality to transform Python source code by injecting exception
watching logic into try blocks for enhanced exception handling.

This module provides a `transform_source` function to enable the transformation
of Python source code. It modifies `try` and `try ... try_star` blocks to wrap
their bodies with exception-watching logic.

Classes:
- `_TryInjector`: A `NodeTransformer` subclass for handling AST `Try` and
  `TryStar` nodes.

Functions:
- `transform_source`: Transforms source code by applying `_TryInjector` logic.
"""

import ast
import types
from typing import override

from ._common import WATCHER_KEY


class _TryInjector(ast.NodeTransformer):
    def __init__(self) -> None:
        self._depth: int = 0

    # Are available in the global namespace the following:
    # - WATCHER_KEY: with(*exceptions)
    @staticmethod
    def _make_transform(
        node: ast.Try | ast.TryStar,
        handlers: list[ast.ExceptHandler],
    ) -> list[ast.stmt]:
        exc_types: list[ast.expr] = []
        for h in handlers:
            if h.type is None:
                exc_types.append(ast.Name(id="BaseException", ctx=ast.Load()))
                continue
            if isinstance(h.type, ast.Tuple):
                exc_types.extend(h.type.elts)
            else:
                exc_types.append(h.type)

        with_node = ast.With(
            items=[
                ast.withitem(
                    context_expr=ast.Call(
                        func=ast.Name(id=WATCHER_KEY, ctx=ast.Load()),
                        args=exc_types,
                        keywords=[],
                    ),
                    optional_vars=None,
                ),
            ],
            body=node.body,
        )

        ast.copy_location(with_node, node)
        ast.fix_missing_locations(with_node)
        node.body = [with_node]
        return [node]

    @override
    def visit_Try(self, node: ast.Try) -> list[ast.stmt]:  # pylint: disable=invalid-name
        """
        Visit a Try node.

        This method is called when a Try node is encountered in the AST.

        Args:
            node: The Try node to be visited.

        Returns:
            list[ast.stmt]: The transformed list of statements.
        """
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1
        return self._make_transform(node, node.handlers)

    @override
    def visit_TryStar(self, node: ast.TryStar) -> list[ast.stmt]:  # pylint: disable=invalid-name
        """
        Visit a TryStar node.

        This method is called when a TryStar node is encountered in the AST.

        Args:
            node: The TryStar node to be visited.

        Returns:
            list[ast.stmt]: The transformed list of statements.
        """
        self._depth += 1
        self.generic_visit(node)
        self._depth -= 1
        return self._make_transform(node, node.handlers)


def transform_source(source: str, filename: str) -> types.CodeType:
    """
    Transforms source code to inject exception watching logic into try blocks.

    Args:
        source: The Python source code to be transformed.
        filename: The name of the file containing the source code.

    Returns:
        types.CodeType: The transformed code object.
    """
    tree = ast.parse(source, filename=filename)
    tree = _TryInjector().visit(tree)
    ast.fix_missing_locations(tree)
    return compile(tree, filename, "exec")


__all__ = ("transform_source",)
