import types

from dramafever.premium.services.policy import (
    unless_errors, wrap_context,

    PolicyRule, PolicyRuleFunc
)


def ctx_apply(f, got, remaining):
    """
    Creates a promise to call `f` with some values corresponding to
    the contextual values (or regular values) in `remaining`, accumulating
    the true values in `got`.

    `f` is then called when remaining is empty, and got is full.
    """
    # base case:
    if not remaining:
        if got:
            return f(*got)
        return f

    # recursive step:
    first, rest = remaining[0], remaining[1:]

    # so, depending on how exactly `first` is not a value:
    if hasattr(first, 'finalize'):
        # if it's a subcontext, finalize it to a policy rule,
        # then add the policy rule back to `remaining` and recurse
        value = first.finalize()
        return ctx_apply(f, got, (value,)+rest)

    if hasattr(first, 'bind'):
        # if it's a policy rule, we're going to have to wait until
        # the policy monad evaluates. so we bind the policy rule to
        # a function that moves the value over to `got` and recurses
        # there.
        #
        # (one might notice that Context never really accesses
        # the value... by the time a request comes in and policy is
        # evaluated, the underlying Context object will long have since
        # been finalized() and possibly even GC'd. Context only does
        # syntactic policy rule manipulation.)
        return first >> (lambda value:
                         ctx_apply(f, got+[value], rest))

    # a regular, plain-ol' value!? bam. lists.
    return ctx_apply(f, got+[first], rest)


class BaseContext(object):
    """
    Underlying implementation of the Context policy builder.

    Contexts comprise two parts:
        1. A wrapper that takes a list of policy rules and returns
           a single policy rule
        2. A list of policy rules and subcontexts

    ctx.finalize() collects this list, finalizes all subcontexts, and wraps
    the resulting list of policy rules into a single policy rule.

    The Context `append` operation is a bit sophisticated:
    A PolicyRuleFunc may be given to append, with a list of values and/or
    _contextual values_, in place of calling the function straightly
    with the values as arguments.

    Contextual values are one of two things: either a policy rule that returns
    some value, or a Context object that finalize()s to a policy rule that
    returns some value. In either case... there's a value we're after, we just
    don't have it yet. So we need to remember everything we do to that value
    until the value exists. (Contextual values can also just be straight
    values)

    Once we have this, we can come very close to writing policies as if they
    were just regular operations on python variables.
    """
    def __init__(self, wrapper=None, *ctx_args, **kwargs):
        self.items = []
        self.ctx_name = kwargs.get('name', None)

        if wrapper is None:
            wrapper = lambda policy_rules: unless_errors(*policy_rules)

        self.wrapper = wrapper
        self.ctx_args = ctx_args

    @staticmethod
    def is_policy_rule(value):
        return isinstance(value, PolicyRule)

    @staticmethod
    def is_policy_rule_func(value):
        return isinstance(value, PolicyRuleFunc)

    def append(self, item, *args):
        """
        Append a policy operation to the Context.

        If it's a regular function or a policy rule function, and *args
        are supplied, use ctx_apply to create a "promise" and append
        that instead.
        """
        if (
                type(item) == types.FunctionType or
                self.is_policy_rule_func(item)
        ):
            self.items.append(ctx_apply(item, [], args))
        else:
            self.items.append(item)
        return self

    def finalize(self):
        """
        Performs all syntactic manipulations to subcontexts and contained
        policy rules and returns a single policy rule aggregate.
        """
        wrapped = self.wrap(self.finalized_items)

        return wrapped

    def subctx(self, wrapper=None, *ctx_args):
        """
        Creates and returns another Context contained within this one.
        Much like `append`, can be provided *ctx_args that is used
        to convert `wrapper` into a promise for when the `ctx_args` are
        resolved to values.

        `wrapper`'s type is one of two things:
          - Either a function from a list of policy rules to 1 policy rule
          - or, a function(policy_rules) to a function(*ctx_args) that
            returns 1 policy rule
        """
        sub = self.__class__(wrapper, *ctx_args)
        self.append(sub)
        return sub

    def named_subctx(self, name, wrapper=None, *ctx_args):
        sub = self.__class__(wrapper, *ctx_args)
        sub.ctx_name = name
        self.append(sub)
        return sub

    def wrap(self, items):
        wrapped = ctx_apply(self.wrapper(items), [], self.ctx_args)
        # if the Context has the ctx_name property, wrap the final policy
        # rule in a `wrap_context` operator.
        if self.ctx_name:
            ctx_frame = ContextFrame(self.ctx_name, wrapped.ast)

            wrapped = wrap_context(ctx_frame, wrapped)
        return wrapped

    @property
    def finalized_items(self):
        return [
            self._finalize_item(item)
            for item in self.items
            if self._warrants_inclusion(item)
        ]

    @staticmethod
    def _finalize_item(item):
        if hasattr(item, 'finalize'):
            return item.finalize()
        return item

    @staticmethod
    def _warrants_inclusion(item):
        """
        Just to note, as an optimization, don't include policies for
        subcontexts that contain no operations
        """
        if not hasattr(item, 'finalize'):
            return True
        subctx = item
        return len(subctx.items) > 0


class ContextFrame(object):
    def __init__(self, name, ast):
        self.name = name
        self.policy_ast = ast

    def __repr__(self):
        return "<policy '{}'>".format(self.name)




