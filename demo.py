import collections
import lazex


@lazex.me
def bar(*args, **kwargs):
    print("In bar")
    expr = args[0]
    assert isinstance(expr, lazex.Expression)

    print("Expressions:", args, kwargs)
    print("In this context, x is", expr.evaluate("x"))
    print("ast:", expr.ast)

    if "/ 0" in expr.escaped:
        print("oh, detected bad operation, returning None instead")
        return None

    y = expr.evaluate()
    return y


@lazex.me
def foo():
    x = 7
    c = collections.Counter()
    rest = [1, 2, 3]
    bla = {"spam": 2}
    print("bar result 1:", bar(x + 4, foo=bar, **bla))
    print()
    x = 8
    print("bar result 2:", bar(x / 0, "hello", *rest))


foo()
