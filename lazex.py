import ast
import inspect
import builtins
from functools import wraps
from collections import defaultdict

import astunparse


registry = set()


def build_attribute_or_name(dotted_name):
    *prefixes, last = dotted_name.split(".")
    res = last
    for prefix in prefixes:
        res = ast.Attribute(ast.Name(prefix), res)
    return res


def build_call(dotted_name, *args, **kwargs):
    name = build_attribute_or_name(dotted_name)
    arguments = []
    arguments.extend(ast.Constant(arg, kind=None) for arg in args)
    return ast.Call(name, args=arguments, keywords=[])


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
                build_call(
                    "lazex.build_expression",
                    astunparse.unparse(node.func),
                    astunparse.unparse(patch_tree(k.value, globals, seen=seen)).rstrip("\n"),
                ),
            )
            for k in node.keywords
        ]
        new_args = []
        for arg in node.args:
            arg = patch_tree(arg, globals, seen=seen)
            unparsed = astunparse.unparse(arg).rstrip("\n")
            if not unparsed.startswith("*"):
                new_args.append(
                    build_call(
                        "lazex.build_expression",
                        astunparse.unparse(node.func),
                        unparsed,
                    )
                )
            else:
                node.keywords.append(
                    ast.keyword(
                        "__args",
                        build_call(
                            "lazex.build_expression",
                            astunparse.unparse(node.func),
                            unparsed[1:],
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
        tree = patch_tree(tree, fn.__globals__,)
        result = astunparse.unparse(tree)
        code = compile(result, fn.__code__.co_filename, "exec")
        fn.__code__ = code.co_consts[0]
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
