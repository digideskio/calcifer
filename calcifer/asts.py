from abc import ABCMeta
import collections
import copy
import re
from six import string_types

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

    def __new__(cls, *operands):
        return super(Node, cls).__new__(cls)

    def __deepcopy__(self, memo):
        return copy.copy(self)

def flatten(l):
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el, string_types):
            for sub in flatten(el):
                yield sub
        else:
            yield el

class Binding(Node):
    def __new__(cls, *operands):
        operands = flatten([
            operand if not isinstance(operand, cls) else operand.operands
            for operand in operands
        ])
        return super(Binding, cls).__new__(cls, operands)

    def __init__(self, *operands):
        self.operands = operands

    def __repr__(self):
        return " >> ".join([repr(operand) for operand in self.operands])

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
