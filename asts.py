from abc import ABCMeta
import re

def get_call_repr(func_name, *args, **kwargs):
    args_expr = ", ".join([repr(arg) for arg in args])
    kwargs_expr = ", ".join([
        "{k}={v}".format(k=k, v=repr(v))
        for k, v in kwargs.items()
    ])
    call_expr = "{name}(".format(name=func_name)
    call_expr += args_expr
    if args_expr and kwargs_expr:
        call_expr += ", "
    call_expr += kwargs_expr
    call_expr += ")"
    return call_expr

class Node:
    __metaclass__ = ABCMeta


class Binding(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return "{} >> {}".format(repr(self.left), repr(self.right))

class PolicyRuleFunc(Node):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

class PolicyRuleFuncCall(Node):
    def __init__(self, func, args, kwargs, result=None):
        self.func = func
        self.args = [
            getattr(arg, 'ast', arg)
            for arg in args
        ]
        self.kwargs = {
            k: getattr(v, 'ast', v)
            for k, v in kwargs.items()
        }
        self.result = result

    def with_result(self, result):
        return PolicyRuleFuncCall(
            self.func,
            self.args,
            self.kwargs,
            result
        )

    def __repr__(self):
        if isinstance(self.func, Node):
            func_name = repr(self.func)
        else:
            func_name = self.func

        identifier = re.compile(r"^[^\d\W]\w*\Z", re.UNICODE)

        if not re.match(identifier, func_name):
            func_name = "({})".format(func_name)

        return get_call_repr(func_name, *self.args, **self.kwargs)
