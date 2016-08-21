import copy
import functools
import logging

from calcifer.operators import (
    wrap_context, attempt, trace, collect, unit, policies, regarding,
    fail,
)
from calcifer.monads import (
    PolicyRule, PolicyRuleFunc, get_call_repr
)

logger = logging.getLogger(__name__)


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
        self.error_handler = None

        if wrapper is None:
            wrapper = self.__class__.get_default_wrapper()

        self.wrapper = wrapper
        self.ctx_args = ctx_args

    @staticmethod
    def get_default_wrapper():
        return lambda policy_rules: policies(*policy_rules)

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
        def make_action(ctx_wrapper, ctx_name, error_handler, num_ctx_args):
            @functools.wraps(ctx_wrapper)
            def action(items):
                ctx_args = items[0:num_ctx_args]
                items = items[num_ctx_args:]
                wrapped = ctx_apply(ctx_wrapper(items), [], ctx_args)

                if ctx_name:
                    if error_handler:
                        handler_rule = error_handler.finalize()
                        ctx_frame = ContextFrame(
                            ctx_name, wrapped.ast, handler_rule
                        )
                    else:
                        ctx_frame = ContextFrame(
                            ctx_name, wrapped.ast
                        )

                    wrapped = wrap_context(ctx_frame, wrapped)
                return wrapped
            return action

        action = make_action(
            self.wrapper,
            self.ctx_name,
            self.error_handler,
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
        catch = attempt_ctx.trace(attempt_ctx.value)

        return attempt_ctx, catch

    def trace(self, value=None):
        def trace_for_policy_rules(policy_rules):
            def trace_for_true_value(true_value):
                return unit(true_value) >> trace(*policy_rules)
            return trace_for_true_value

        return self.subctx(trace_for_policy_rules, value)

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
        def apply_for_policy_rules(policy_rules):
            def apply_for_true_args(*true_args):
                return collect(*policy_rules)(func(*true_args))
            return apply_for_true_args

        if hasattr(func, '__name__'):
            func_name = func.__name__
        else:
            func_name = '<anonymousfunction>'

        apply_ctx = self.named_subctx(
            "apply({})".format(func_name),
            apply_for_policy_rules,
            *args
        )
        return apply_ctx

    def memoized_apply(self, func, *args):
        class MemoKey(object):
            def __init__(self, *true_args):
                self.true_args = true_args

            def __lt__(self, other):
                return self.true_args < other.true_args

            def __hash__(self):
                return make_hash( self.true_args )

            def __repr__(self):
                return "<MemoKey {}>".format(
                    get_call_repr(*self.true_args)
                )

        @functools.wraps(func)
        def memoized_func(*true_args):
            if not hasattr(memoized_func, 'memo'):
                memoized_func.memo = {}
            memo = memoized_func.memo
            key = MemoKey(*true_args)
            if key in memo:
                logger.debug("Found memo key: %r", key)
                return memo[key]
            result = func(*true_args)
            logger.debug("Adding memo key: %r", key)
            logger.debug("Existing memo keys: %r", memo.keys())
            memo[key] = result
            return result

        return self.apply(memoized_func, *args)

    def check(self, func, *func_args):
        def make_check_wrapper(func):
            def check_wrapper(policy_rules):
                def eval_wrapper(*true_func_args):
                    func_result = func(*true_func_args)
                    if func_result:
                        return collect(*policy_rules)(func_result)
                    else:
                        return policies()
                return eval_wrapper
            return check_wrapper

        ctx_name = "check({})".format(func.__name__)
        subctx = self.named_subctx(
            ctx_name,
            make_check_wrapper(func),
            *func_args
        )
        return subctx

    def scope_item_subctx(self, parent, child, name=None):
        def scope_item_subctx_for_policy_rules(policy_rules):
            def scope_item_subctx_for_true_relations(true_parent, true_child):
                return regarding(
                    "{}/{}".format(true_parent, true_child),
                    *policy_rules
                )
            return scope_item_subctx_for_true_relations
        subctx = self.subctx(scope_item_subctx_for_policy_rules, parent, child)
        if name is not None:
            subctx.ctx_name = name
        return subctx

    def scope_subctx(self, scope, name=None):
        def scope_subctx_for_policy_rules(policy_rules):
            def scope_subctx_for_true_scope(true_scope):
                return regarding(true_scope, *policy_rules)
            return scope_subctx_for_true_scope
        subctx = self.subctx(scope_subctx_for_policy_rules, scope)
        if name is not None:
            subctx.ctx_name = name
        return subctx

    def select(self, scope):
        return self.scope_subctx(scope, 'select("{}")'.format(scope))

    def fail(self):
        self.append(fail())
        return self

    def __repr__(self):
        return (
            "<{} name='{}'>"
        ).format(self.__class__.__name__, self.ctx_name)


class ContextFrame(object):
    def __init__(self, name, ast, error_handler=None):
        self.name = name
        self.policy_ast = ast
        self.error_handler = error_handler

    def __repr__(self):
        return "<policy '{}'>".format(self.name)

    def __deepcopy__(self, memo):
        # you get a new object but you're not copying that AST
        return ContextFrame(self.name, self.policy_ast, self.error_handler)


# from http://stackoverflow.com/questions/5884066/hashing-a-python-dictionary
def make_hash(o):
    """
    Makes a hash from a dictionary, list, tuple or set to any level, that contains
    only other hashable types (including any lists, tuples, sets, and
    dictionaries).
    """
    if isinstance(o, (set, tuple, list)):
        return hash(tuple([make_hash(e) for e in o]))
    elif not isinstance(o, dict):
        return hash(o)

    new_o = copy.deepcopy(o)
    for k, v in new_o.items():
        new_o[k] = make_hash(v)

    return hash(tuple(frozenset(sorted(new_o.items()))))
