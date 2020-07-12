import ast
import inspect
import astunparse


def patch_tree(tree):
    # Walk the tree and patch function calls.
    # How do we only replace function calls to patched functions?
    import ipdb; ipdb.set_trace()
    ...
    return tree


def me(fn):
    # decorator
    source = inspect.getsource(fn)
    decorator, def_, rest = source.partition("def ")
    source = def_ + rest
    tree = ast.parse(source)
    tree = patch_tree(tree)
    result = astunparse.unparse(tree)
    code = compile(result, fn.__code__.co_filename, "exec")
    fn.__code__ = code.co_consts[0]
    return fn


class Expr:
    ...
