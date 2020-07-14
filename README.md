# plazy

`plazy` is a small library that enables your functions to customize
how arguments are given to it. For example, such a function `foo` that you call
with an expression, say `foo(2 + 3)` does not just get the value `5` as a
parameter, but knows the 5 came from adding `2` and `3`. In fact, it can even
prevent evaluation of this expression and do whatever it wants with it.

In order to use this, you need to import the library:

    import plazy

Make sure to import it exactly like that and not under a different name,
otherwise it will not work.

Next, decorate your functions with the decorator `plazy.me`. This is an
identity function (the equivalent of `lambda x: x`):

```python
@plazy.me
def foo(something):
    return something.evaluate()
```
