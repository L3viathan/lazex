import lazex

@lazex.me
def foo(something, ham=None):
    if ham:
        return something.escaped, ham.escaped
    return something.escaped

@lazex.me
def bar():
    return foo(x / 0)

@lazex.me
def bat():
    return foo(3 + int(5), ham=str(4))

def test_local_scope():
    x = 7
    arg = lazex.Expression("x+3")
    assert arg.evaluate() == 10


def test_escaped():
    assert bar() == "(x / 0)"


def test_nested_call_clean():
    assert bat() == ("(3 + int(5))", "str(4)")
