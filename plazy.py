import ast
import uuid
import inspect
import builtins
from functools import wraps

import astunparse


registry = set()
namespaces = {}


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


def patch_tree(tree, globals):
    # Walk the tree and patch function calls.
    # How do we only replace function calls to patched functions?
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = get_obj_from_func(node.func, globals)
        if hasattr(fn, "__wrapped__") and fn.__wrapped__ in registry:
            print("Patching")
            ID = uuid.uuid4().hex
            node.args = [
                ast.Call(
                    ast.Attribute(ast.Name("plazy"), "Expr"),
                    args=[
                        ast.Constant(
                            f"{ID}@@{astunparse.unparse(node.args[0])}", kind=None
                        )
                    ],
                    keywords=[],
                )
            ]
            namespace = dict(builtins.__dict__)
            namespace.update(globals)
            namespaces[ID] = namespace
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


class Expr:
    def __init__(self, expr):
        caller_locals = inspect.currentframe().f_back.f_locals
        self.ID, _, self.expr = expr.partition("@@")
        self.namespace = namespaces[self.ID]
        self.namespace.update(caller_locals)
        self.evaluated = {}

    def evaluate(self, expr=None):
        if expr in self.evaluated:
            return self.evaluated[expr]
        self.evaluated[expr] = eval(self.expr if expr is None else expr, self.namespace)
        return self.evaluated[expr]
