# lazex

`lazex` (short for "lazy expressions") is a small library that enables your
functions to customize how arguments are given to it. For example, such a
function `foo` that you call with an expression, say `foo(2 + 3)` does not just
get the value `5` as a parameter, but knows the 5 came from adding `2` and `3`.
In fact, it can even prevent evaluation of this expression and do whatever it
wants with it.

In order to use this, you need to import the library:

    import lazex

Make sure to import it exactly like that and not under a different name,
otherwise it will not work.

Next, decorate your functions with the decorator `lazex.me`. This is an
identity function (the equivalent of `lambda x: x`):

```python
@lazex.me
def foo(something):
    return something.evaluate()
```

A more realistic function might inspect the arguments and tell you how the
result was obtained:

```python
@latex.me
def explain(expr):
    return f"The answer to {expr.escaped} is [expr.evaluate()}"
```


If you now call `explain(2+3)`, it will return you the string "The answer to (2
\+ 3) is 5".

Here's the catch: In order for this to work, the calling function must _also_
have been decorated with `latex.me`. This is sadly a consequence of the fact
that what we're doing here is not usually possible in Python.

----

Even without this decorator, you can still use `lazex` to define expressions in
a given context that you may or may not want to evaluate later:

```python
def outer():
    x = 7
    y = lazex.Expression('x * 14')
    inner(y)

def inner(expr):
    import random
    if random.random() > 0.5:
        print(expr.evaluate())
```

While this toy example may seem silly, you can wrap arbitrarily complex [expressions](https://docs.python.org/3/reference/expressions.html). For example, you could delay a complex function call that might need to occur:

```python
id_ = '1274897d129d24'
doc = complex.framework.get_document_by_id(id_, reticulate_splines='force')
delete = lazex.Expression(
    'complex.framework.delete_from_db('
    'doc, id_, safe_delete=True, cleanup=False,'
    'restore_function=complex.framework.restore_with_trick).confirmation_id'
)
process_document(doc, deleteexpr=delete)
```

Here, the `process_document` function may at some point decide that it needs to
delete the document, and can just call `delete.evaluate()`. Sure, this is also
solvable with a simple lambda, but if you were looking for straightforward,
idiomatic solutions you've come to the wrong place.

## Technical details

If you want to know how this works, just look at `lazex.py`, it's barely more
than a hundred lines. Here's the gist:

- Register all functions decorated by `lazex.me` as magical lazex functions,
  and replace them with a wrapper.
- When the wrapper is run, we check if we have already patched the function. If
  so, we just call the original function with the given arguments.
- Otherwise, we patch it:
    - First, we use `inspect.getsource()` to get the original source code of
      the function.
    - Next, we parse the source code with `ast.parse()`. We then walk over all
      nodes of the AST, until we find an `ast.Call` (a function call):
    - Given the function's `__globals__` (the global namespace where the
      function was defined), we retrieve the object that is being called here.*
    - If this callee was'nt previously registered through the decorator, we
      abort and continue with the next `ast.Call`.
    - Otherwise, we use the `astunparse` library to get a string representation
      of all expressions that are given as positional and keyword arguments,
      and replace the corresponding nodes with yet another `ast.Call` node that
      will instantiate a `lazex.Expression`.
    - Effectively, this will replace a call like `foo(1 + 2, x, bar=bat)` with
      `foo(Expression("1 + 2"), Expression("x"), bar=Expression("bat"))`.
    - The modified AST is then fed to `astunparse` to generate source code,
      that source code is executed using `compile()` and the resulting code
      object is set as the new `.__code__` attribute of the original function.
- We then execute the patched function with the original arguments. When we
  reach a call to a lazex function, a new `Expression` object is created.
- Here, we use `inspect.currentframe().f_back` to get a reference to the
  _previous_ execution frame, in order to retrieve its local and global
  namespace (the `.f_locals` and `.f_globals` attributes on the frame object).
- After saving these namespaces on our `Expression` instance, we can now use it
  to access the original source code, as well as the AST for this specific
  expression. When we want to evaluate the expression, we can use the
  namespaces with `eval` in order to produce the correct values.

\* This is one of the spots where something can go wrong: If a global reference
changes between executions of the function, this will return the wrong
callable. This is probably sufficiently rare that it won't matter most of the
time. Similar problems occur when the callable _isn't_ in the global namespace
(e.g. when it is defined locally).
