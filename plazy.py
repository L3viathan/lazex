import ast
import inspect
import builtins
from functools import wraps
from collections import defaultdict

import astunparse


registry = set()


def get_obj_from_func(func, globals):
    try:
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            obj = get_obj_from_func(func.value, globals)
            attr = func.attr
            return getattr(obj, attr)
        return globals.get(name) or getattr(builtins, name, None)
    except AttributeError:
        return None


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


def patch_tree(tree, globals):
    # Walk the tree and patch function calls.
    # How do we only replace function calls to patched functions?
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = get_obj_from_func(node.func, globals)
        if hasattr(fn, "__wrapped__") and fn.__wrapped__ in registry:
            node.keywords = [
                ast.keyword(
                    (k.arg or "__kwargs"),
                    build_call(
                        "plazy.Expression",
                        astunparse.unparse(k.value).rstrip("\n"),
                    ),
                )
                for k in node.keywords
            ]
            new_args = []
            for arg in node.args:
                unparsed = astunparse.unparse(arg).rstrip("\n")
                if not unparsed.startswith("*"):
                    new_args.append(
                        build_call("plazy.Expression", unparsed)
                    )
                else:
                    node.keywords.append(
                        ast.keyword(
                            "__args",
                            build_call(
                                "plazy.Expression",
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
        if hasattr(fn, "_plazy_patched") and fn._plazy_patched:
            return fn(*args, **kwargs)
        source = inspect.getsource(fn)
        _, def_, rest = source.partition("def ")
        source = def_ + rest
        tree = ast.parse(source)
        tree = patch_tree(tree, fn.__globals__,)
        result = astunparse.unparse(tree)
        code = compile(result, fn.__code__.co_filename, "exec")
        fn.__code__ = code.co_consts[0]
        fn._plazy_patched = True
        return fn(*args, **kwargs)

    return wrapper


class Expression:
    def __init__(self, value):
        self.escaped = value
        caller_frame = inspect.currentframe().f_back
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
        if expr in self._cache[method]:
            return self._cache[method][expr]
        if expr is None:
            expr = self.escaped
        self._cache[method][expr] = self.transform_one(expr, method=method)
        return self._cache[method][expr]

    def evaluate(self, expr=None):
        return self.transform(expr=expr, method="eval")

    @property
    def ast(self):
        return self.transform(expr=None, method="ast")

    def __repr__(self):
        return f"«{self.escaped}»"
