import ast
import inspect
import builtins

import astunparse


def get_obj_from_func(func, locals, globals):
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        obj = get_obj_from_func(func.value, locals, globals)
        attr = func.attr
        return getattr(obj, attr)
    return locals.get(name) or globals.get(name) or getattr(builtins, name)


def patch_tree(tree, globals, locals):
    # Walk the tree and patch function calls.
    # How do we only replace function calls to patched functions?
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = get_obj_from_func(node.func, locals, globals)
        import ipdb; ipdb.set_trace()
    return tree


def me(fn):
    # decorator
    source = inspect.getsource(fn)
    decorator, def_, rest = source.partition("def ")
    source = def_ + rest
    tree = ast.parse(source)
    fn.__code__.co_varnames
    fn.__code__.co_nlocals
    import ipdb; ipdb.set_trace()
    tree = patch_tree(
        tree,
        fn.__globals__,
        dict(
            zip(
                fn.__code__.co_varnames, fn.__code__.co_consts[fn.__code__.co_nlocals :]
            )
        ),
    )
    result = astunparse.unparse(tree)
    code = compile(result, fn.__code__.co_filename, "exec")
    fn.__code__ = code.co_consts[0]
    return fn


class Expr:
    ...
