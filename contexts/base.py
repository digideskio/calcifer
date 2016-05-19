import copy
import functools

from dramafever.premium.services.policy.operators import (
    unless_errors, wrap_context, attempt, trace, collect, unit,
)
from dramafever.premium.services.policy.monads import (
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


def wrap_ctx_values(action, args):
    """
    Run some function `action` on args that may be ContextualValues
    (Values provided by a Context's wrapper)
    """
    missing_args = get_missing(args)
    if missing_args:
        return make_incomplete(
            action,
            args,
            missing_args
        )

    return action(args)


def get_missing(args):
    """
    Determine which args are missing obtainable values
    """
    missing_args = set()
    for arg in args:
        if isinstance(arg, ContextualValue):
            missing_args.add(arg)
        if isinstance(arg, Incomplete):
            missing_args.update(arg.missing)

    return missing_args


def make_incomplete(f, args_, missing_args):
    """
    Make a function that takes a dictionary of {ctx_value: true_value}s
    and maps to f(*args) in the right order.
    """
    @functools.wraps(f)
    def complete(true_values):
        args = []
        for arg in args_:
            if isinstance(arg, ContextualValue):
                args.append(true_values[arg])
            elif isinstance(arg, Incomplete):
                got = {
                    ctx_value: true_values[ctx_value]
                    for ctx_value in arg.missing
                }
                args.append(arg.complete(got))
            else:
                args.append(arg)

        return f(tuple(args))

    incomplete = Incomplete(
        func=complete,
        missing=missing_args
    )

    return incomplete


class ContextualValue(object):
    """
    A value that exists in transmission between policy operators.
    Specifically, a value provided by some Context wrapper.

    For instance:

    ctx.each() becomes:
       children() >> each( ... )

    And inside that `each( ... )` is information (field value) that is
    not obtainable elsewhere (due to generic name of `each`)
    """
    def __init__(self, ctx):
        self.ctx = ctx

    def __hash__(self):
        return hash(self.ctx)

    def __eq__(self, other):
        return isinstance(other, ContextualValue) and self.ctx == other.ctx

    def __ne__(self, other):
        return not(self == other)


class Incomplete(object):
    def __init__(self, func, missing, got=None):
        self.missing = missing
        if got is None:
            got = {}
        self.got = got
        self.func = func

    def complete(self, true_values):
        got = copy.copy(self.got)
        missing = copy.copy(self.missing)

        got.update(true_values)
        missing -= set(true_values.keys())

        if not missing:
            return self.func(got)

        return Incomplete(
            func=self.func,
            missing=missing,
            got=got
        )

    def __repr__(self):
        return (
            "Incomplete(missing={})"
        ).format(set([missing.ctx for missing in self.missing]))


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
            wrapper = self.__class__.get_default_wrapper()

        self.wrapper = wrapper
        self.ctx_args = ctx_args

    @staticmethod
    def get_default_wrapper():
        return lambda policy_rules: unless_errors(*policy_rules)

    @staticmethod
    def is_policy_rule(value):
        return isinstance(value, PolicyRule)

    @staticmethod
    def is_policy_rule_func(value):
        return isinstance(value, PolicyRuleFunc)

    @property
    def value(self):
        return ContextualValue(self)

    def append(self, item, *args):
        """
        Append a policy operation to the Context.

        If it's a regular function or a policy rule function, and *args
        are supplied, use ctx_apply to create a "promise" and append
        that instead.
        """
        if not args:
            self.items.append(item)
        else:
            self.items.append(
                wrap_ctx_values(
                    lambda args: ctx_apply(item, [], args),
                    args
                )
            )
        return self

    def finalize(self):
        """
        Performs all syntactic manipulations to subcontexts and contained
        policy rules and returns a single policy rule aggregate.
        """
        finalized_items = self.get_finalized_items()
        wrapped = self.wrap(finalized_items)

        return wrapped

    def get_finalized_items(self):
        return [
            self._finalize_item(item, getattr(self, 'value', None))
            for item in self.items
            if self._warrants_inclusion(item)
        ]

    @classmethod
    def _finalize_item(cls, item, provided_ctx_value=None):
        finalize_item = cls._finalize_item

        if hasattr(item, 'finalize'):
            return finalize_item(item.finalize(), provided_ctx_value)
        if isinstance(item, Incomplete) and provided_ctx_value in item.missing:
            def make_appended_func(item, ctx_value):
                @functools.wraps(item.func)
                def appended_func(value):
                    return item.complete({ctx_value: value})
                return appended_func

            def make_incomplete_func(item, ctx_value):
                @functools.wraps(item.func)
                def incomplete_func(true_values):
                    missing_one = item.complete(true_values)
                    return make_appended_func(missing_one, ctx_value)
                return incomplete_func


            missing = item.missing - set([provided_ctx_value])
            if not missing:
                return make_appended_func(item, provided_ctx_value)

            return Incomplete(
                func=make_incomplete_func(item, provided_ctx_value),
                missing=missing
            )
        return item

    def wrap(self, items):
        def make_action(ctx_wrapper, ctx_name, num_ctx_args):
            def action(items):
                ctx_args = items[0:num_ctx_args]
                items = items[num_ctx_args:]
                wrapped = ctx_apply(ctx_wrapper(items), [], ctx_args)

                if ctx_name:
                    ctx_frame = ContextFrame(ctx_name, wrapped.ast)
                    wrapped = wrap_context(ctx_frame, wrapped)
                return wrapped
            return action

        action = make_action(
            self.wrapper,
            self.ctx_name,
            len(self.ctx_args)
        )

        wrapped = wrap_ctx_values(
            action,
            self.ctx_args + tuple(items)
        )
        return wrapped

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

    def attempt_catch(self):
        def attempt_wrapper(policy_rules):
            catch_rule = policy_rules[0]
            policy_rules = policy_rules[1:]
            return attempt(
                *policy_rules,
                catch=catch_rule
            )

        attempt_ctx = self.subctx(attempt_wrapper)
        catch = attempt_ctx.subctx().trace(attempt_ctx.value)

        return attempt_ctx, catch

    def trace(self, value=None):
        return self.subctx(
            lambda policy_rules: (
                lambda true_value: (
                    unit(true_value) >> trace(*policy_rules)
                )
            ),
            value
        )

    def or_catch(self):
        """
        Rebuild items so that the last thing was actually done in an
        attempt/catch context
        """
        last = self.items.pop()
        attempt_ctx, catch_ctx = self.attempt_catch()
        attempt_ctx.append(last)
        return catch_ctx

    def apply(self, func, *args):
        if hasattr(func, '__name__'):
            func_name = func.__name__
        else:
            func_name = '<anonymousfunction>'

        apply_ctx = self.named_subctx(
            "apply({})".format(func_name),
            lambda policy_rules: (
                lambda *true_args: (
                    collect(*policy_rules)(func(*true_args))
                )
            ),
            *args
        )
        return apply_ctx

    def __repr__(self):
        return (
            "<{} name='{}'>"
        ).format(self.__class__.__name__, self.ctx_name)


class ContextFrame(object):
    def __init__(self, name, ast):
        self.name = name
        self.policy_ast = ast

    def __repr__(self):
        return "<policy '{}'>".format(self.name)

    def __deepcopy__(self, memo):
        # you get a new object but you're not copying that AST
        return ContextFrame(self.name, self.policy_ast)
