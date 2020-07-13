import collections
import plazy


@plazy.me
def bar(arguments):
    print("In bar")
    assert isinstance(arguments, plazy.Arguments)

    print("Arguments:", arguments)
    print("In this context, x is", arguments.evaluate("x"))
    print("ast:", arguments.ast())

    if "/ 0" in arguments.args[0]:
        print("oh, detected bad operation, returning None instead")
        return None

    y = arguments.evaluate()
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
