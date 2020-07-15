import lazex

@lazex.me
def foo(something):
    return something.escaped

@lazex.me
def bar():
    return foo(x / 0)

def test_local_scope():
    x = 7
    arg = lazex.Expression("x+3")
    assert arg.evaluate() == 10


def test_escaped():
    assert bar() == "(x / 0)"
