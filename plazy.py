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


def build_attribute_or_name(dotted_name):
    *prefixes, last = dotted_name.split(".")
    res = last
    for prefix in prefixes:
        res = ast.Attribute(ast.Name(prefix), res)
    return res


def build_call(dotted_name, ID, *args, **kwargs):
    name = build_attribute_or_name(dotted_name)
    arguments = [ast.Constant(ID, kind=None)]
    arguments.extend(ast.Constant(arg, kind=None) for arg in args)
    keywords = [
        ast.keyword(arg=k, value=ast.Constant(v, kind=None))
        for (k, v) in kwargs.items()
    ]
    return ast.Call(name, args=arguments, keywords=keywords,)


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
                build_call(
                    "plazy.Arguments",
                    ID,
                    *(astunparse.unparse(arg).rstrip("\n") for arg in node.args),
                    **{
                        (k.arg or "__kw"): astunparse.unparse(k.value).rstrip("\n")
                        for k in node.keywords
                    }
                )
            ]
            node.keywords = []
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


class Arguments:
    def __init__(self, ID, *args, **kwargs):
        self.ID = ID
        self.args = tuple(arg for arg in args if not arg.startswith("*"))
        self.kwargs = {k: v for (k, v) in kwargs.items() if k != "__kw"}
        star_args = [arg for arg in args if arg.startswith("*")]
        self.star_args = star_args[0][1:] if star_args else None
        self.star_kwargs = kwargs["__kw"] if "__kw" in kwargs else None
        caller_locals = inspect.currentframe().f_back.f_locals
        self.namespace = namespaces[self.ID]
        self.namespace.update(caller_locals)
        self.evaluated = {}

    def evaluate(self, expr=None):
        if expr in self.evaluated:
            return self.evaluated[expr]
        if expr is not None:
            if isinstance(expr, int):
                self.evaluated[expr] = eval(self.args[expr], self.namespace)
            elif isinstance(expr, str) and expr in self.kwargs:
                self.evaluated[expr] = eval(self.kwargs[expr], self.namespace)
            else:
                self.evaluated[expr] = eval(expr, self.namespace)
        else:
            # return tuple of all
            for i, expr in enumerate(self.args):
                self.evaluated[i] = eval(expr, self.namespace)
            return tuple(self.evaluated[i] for i in range(len(self.args)))
        return self.evaluated[expr]

    def __repr__(self):
        parts = [
            ", ".join(arg for arg in self.args),
            f"*{self.star_args}" if self.star_args else "",
            ", ".join(f"{k}={v}" for (k, v) in self.kwargs.items()),
            f"**{self.star_kwargs}" if self.star_kwargs else "",
        ]
        return "Arguments({})".format(", ".join(part for part in parts if part))

