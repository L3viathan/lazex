import plazy

@plazy.me
def foo():
    x = 7
    print(bar(x + 4))


@plazy.me
def bar(expr):
    import ipdb; ipdb.set_trace()
    assert isinstance(expr, plazy.Expr)
    print(expr.locals)
    print(expr.globals)
    ...
    # Can see that it was "x + 4"
    # Can see that "x" was 7 (maybe expr.evaluate("x")?)
    # Try to never evaluate stuff twice?
    y = expr.evaluate()
    return y

foo()
