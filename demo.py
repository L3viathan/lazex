import collections
import plazy


@plazy.me
def bar(expr, *args, **kwargs):
    print("In bar")
    assert isinstance(expr, plazy.Argument)

    print("Arguments:", args)
    print("In this context, x is", expr.evaluate("x"))
    print("ast:", expr.ast)

    if "/ 0" in expr.escaped:
        print("oh, detected bad operation, returning None instead")
        return None

    y = expr.evaluate()
    return y


@plazy.me
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
