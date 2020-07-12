import collections
import plazy


@plazy.me
def bar(expr):
    print("In bar")
    assert isinstance(expr, plazy.Expr)

    print("Expression:", expr.expr)
    print("In this context, x is", expr.evaluate("x"))

    if "/ 0" in expr.expr:
        print("oh, detected bad operation, returning None instead")
        return None

    y = expr.evaluate()
    return y


@plazy.me
def foo():
    x = 7
    c = collections.Counter()
    print("Calling bar")
    print("bar result 1:", bar(x + 4))
    x = 8
    print("bar result 2:", bar(x / 0))

foo()
