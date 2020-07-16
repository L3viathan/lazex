import ast
import inspect
import builtins
from functools import wraps
from collections import defaultdict

import astunparse


registry = set()


def unparse(something):
    return astunparse.unparse(something).rstrip("\n")


def build_expression_call(*args, **kwargs):
    call = ast.Attribute(
        value=ast.Call(
            func=ast.Name(
                id="__import__",
                ctx=ast.Load(),
            ),
            args=[
                ast.Constant(value="lazex", kind=None),
            ],
            keywords=[],
        ),
        attr="build_expression",
        ctx=ast.Load(),
    )

    arguments = []
    arguments.extend(ast.Constant(arg, kind=None) for arg in args)
    return ast.Call(call, args=arguments, keywords=[])


def patch_tree(tree, globals, seen=None):
    # Walk the tree and patch function calls.
    # How do we only replace function calls to patched functions?
    if seen is None:
        seen = {tree}
    elif tree in seen:
        return tree
    else:
        seen.add(tree)
    for node in list(ast.walk(tree)):  # list() to not consider new nodes
        if not isinstance(node, ast.Call):
            continue
        node.keywords = [
            ast.keyword(
                (k.arg or "__kwargs"),
                build_expression_call(
                    unparse(node.func),
                    unparse(patch_tree(k.value, globals, seen=seen)),
                ),
            )
            for k in node.keywords
        ]
        new_args = []
        for arg in node.args:
            arg = patch_tree(arg, globals, seen=seen)
            unparsed = unparse(arg)
            if not unparsed.startswith("*"):
                new_args.append(
                    build_expression_call(unparse(node.func), unparsed)
                )
            else:
                node.keywords.append(
                    ast.keyword(
                        "__args",
                        build_expression_call(
                            unparse(node.func), unparsed[1:]
                        ),
                    )
                )
        node.args = new_args

    return tree


def me(fn):
    registry.add(fn)
    # decorator
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if hasattr(fn, "_lazex_patched") and fn._lazex_patched:
            return fn(*args, **kwargs)
        source = inspect.getsource(fn)
        _, def_, rest = source.partition("def ")
        source = def_ + rest
        tree = ast.parse(source)
        tree = patch_tree(tree, fn.__globals__)
        result = unparse(tree)
        code = compile(result, fn.__code__.co_filename, "exec")
        fn.__code__ = next(  # I hope this will always be right
            const for const in code.co_consts if isinstance(const, type(fn.__code__))
        )
        fn._lazex_patched = True
        return fn(*args, **kwargs)

    return wrapper


def build_expression(fname, *args, **kwargs):
    caller_frame = inspect.currentframe().f_back
    expr = Expression(*args, _caller_frame=caller_frame, **kwargs)
    fn = expr.evaluate(fname)
    if hasattr(fn, "__wrapped__") and fn.__wrapped__ in registry:
        return expr
    return expr.evaluate()


class Expression:
    def __init__(self, value, _caller_frame=None):
        self.escaped = value
        caller_frame = _caller_frame or inspect.currentframe().f_back
        self.globals = caller_frame.f_globals
        self.locals = caller_frame.f_locals
        self._cache = defaultdict(dict)
        self.strip_internal_nodes()

    def strip_internal_nodes(self):
        AST = self.ast
        for node in list(ast.walk(AST)):
            if not isinstance(node, ast.Call):
                continue
            newargs = []
            for arg in node.args:
                if (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Attribute)
                    and arg.func.attr == "build_expression"
                    and isinstance(arg.func.value, ast.Call)
                    and arg.func.value.func.id == "__import__"
                    and arg.func.value.args[0].value == "lazex"
                ):
                    newargs.append(ast.parse(arg.args[1].value).body[0].value)
                else:
                    newargs.append(arg)
            node.args = newargs
        self.escaped = unparse(AST)

    def transform_one(self, expression, method="eval"):
        if method == "eval":
            return eval(expression, self.globals, self.locals)
        if method == "ast":
            return ast.parse(expression).body[0].value
        raise NotImplementedError

    def transform(self, expr=None, method="eval"):
        if expr is None:
            expr = self.escaped
        if expr in self._cache[method]:
            return self._cache[method][expr]
        self._cache[method][expr] = self.transform_one(expr, method=method)
        return self._cache[method][expr]

    def evaluate(self, expr=None):
        return self.transform(expr=expr, method="eval")

    @property
    def ast(self):
        return self.transform(expr=None, method="ast")

    def __repr__(self):
        return f"«{self.escaped}»"
