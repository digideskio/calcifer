import types

from dramafever.premium.services.policy import (
    policies, regarding, set_value, permit_values, wrap_context, unit_value,
    select, check, require_value, attempt, select, trace, append_value,
    define_as, forbid_value,

    PolicyRule, PolicyRuleFunc,
)
from dramafever.premium.services.policy.contexts.policies import (
    add_fields,
    add_error
)


class ContextFrame(object):
    def __init__(self, name, ast):
        self.name = name
        self.policy_ast = ast

    def __repr__(self):
        return "<policy '{}'>".format(self.name)


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
            wrapper = lambda policy_rules: policies(*policy_rules)

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
        are supplied, use self.ctx_apply to create a "promise" and append
        that instead.
        """
        if (
                type(item) == types.FunctionType or
                self.is_policy_rule_func(item)
        ):
            self.items.append(self.ctx_apply(item, [], args))
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
        wrapped = self.ctx_apply(self.wrapper(items), [], self.ctx_args)
        # if the Context has the ctx_name property, wrap the final policy
        # rule in a `wrap_context` operator.
        if self.ctx_name:
            ctx_frame = ContextFrame(self.ctx_name, wrapped.ast)

            wrapped = wrap_context(ctx_frame, wrapped)
        return wrapped

    @classmethod
    def ctx_apply(cls, f, got, remaining):
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
            return cls.ctx_apply(f, got, (value,)+rest)

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
                             cls.ctx_apply(f, got+[value], rest))

        # a regular, plain-ol' value!? bam. lists.
        return cls.ctx_apply(f, got+[first], rest)

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


class Context(BaseContext):
    """
    `Context` provides a high-level interface for building policies.

    Policies are built by performing stateful operations on Context objects.

    Example usage:

        ctx = Context()
        ctx.consumer_name.require()

        ctx.field("merchant_type").define_as(MerchantTypeField())

        policy = ctx.finalize()

    Method calls/property retrievals modify the Context to potentially
    include additional policy rules, as appropriate.

    Implementation details can be found in BaseContext
    """
    @property
    def consumer_name(self):
        return self.scope_subctx("/sender/consumer_name", "consumer_name")

    @property
    def user_guid(self):
        return self.scope_subctx("/sender/user_guid", "user_guid")

    @property
    def resource_id(self):
        return self.scope_subctx("/receiver/resource_id", "resource_id")

    def require(self):
        subctx = self.named_subctx("require")
        subctx.append(require_value()).or_error()
        return subctx

    def forbid(self):
        subctx = self.named_subctx("forbid")
        subctx.append(forbid_value()).or_error()
        return subctx

    def check(self, func, *func_args):
        def make_check_wrapper(func):
            def check_wrapper(policy_rules):
                def eval_wrapper(*true_func_args):
                    if func(*true_func_args):
                        return policies(*policy_rules)
                    else:
                        return policies()
                return eval_wrapper
            return check_wrapper

        ctx_name = "check({})".format(func.__name__)
        subctx = self.named_subctx(ctx_name,
            make_check_wrapper(func), *func_args
        )
        return subctx

    def scope_item_subctx(self, parent, child, name=None):
        subctx = self.subctx(
            lambda policy_rules: (
                lambda parent_name, child_name: (
                    regarding(
                        "{}/{}".format(parent_name, child_name),
                        *policy_rules
                    )
                )
            ),
            parent, child
        )

        if name is not None:
            subctx.ctx_name = name

        return subctx

    def scope_subctx(self, scope, name=None):
        subctx = self.subctx(
            lambda policy_rules: (
                lambda true_scope: (
                    regarding(
                        "{}".format(scope),
                        *policy_rules
                    )
                )
            ),
            scope
        )
        if name is not None:
            subctx.ctx_name = name

        return subctx

    select = scope_subctx

    def kwarg(self, kwarg_name):
        ctx_name = "kwarg({})".format(kwarg_name)
        return self.scope_item_subctx("/kwargs", kwarg_name, ctx_name)

    @property
    def kwargs(self):
        return self.scope_subctx("/kwargs", "kwargs")

    def set_value(self, value):
        self.append(set_value, value)
        return self

    def append_value(self, value):
        self.append(append_value, value)
        return self

    def add_values(self, values):
        self.append(lambda true_values: (
            policies(*[
                regarding("{}".format(name), set_value(value))
                for name, value in true_values.items()
            ])
        ), values)
        return self

    def query(self, query_name, resource_name, resource_id=None, params=None):
        if params is None:
            params = {}

        def make_query_runner(receiver):
            def query_runner():
                from dramafever.premium.services.dispatch import dispatcher
                query_sender = receiver
                dispatch = dispatcher.connect_as(**query_sender)
                query_receiver = {
                    "resource_name": resource_name,
                    "query_name": query_name,
                }
                if resource_id is not None:
                    query_receiver["resource_id"] = resource_id

                data = {"params": params}

                query_response = dispatch.query(query_receiver, data)

                return query_response['data']
            return query_runner

        return self.subctx(
            lambda policy_rules: (
                select("/receiver") >> unit_value >> (lambda receiver: (
                    check(make_query_runner(receiver))
                ))
            )
        )

    def whitelist_values(self, values):
        subctx = self.named_subctx("whitelist_values")
        subctx.append(permit_values, values).or_error()
        return subctx

    def or_error(self):
        last = self.items.pop()
        subctx = self.subctx(
            lambda policy_rules: (
                attempt(
                    *policy_rules,
                    catch=trace() >> add_error
                )
            )
        )
        subctx.append(last)
        return self


class QueryContext(Context):
    def param(self, param_name):
        ctx_name = "param({})".format(param_name)
        return self.scope_item_subctx("/params", param_name, ctx_name)

    @property
    def params(self):
        return self.scope_subctx("/params", "params")


class CommandContext(Context):
    def field(self, field_name):
        ctx_name = "field({})".format(field_name)
        return self.scope_item_subctx("/fields", field_name, ctx_name)

    @property
    def fields(self):
        return self.scope_subctx("/fields", "fields")

    def add_fields(self, fields_dict):
        self.append(add_fields(fields_dict))
        return self

    def define_as(self, definition):
        self.append(define_as, definition).or_error()
        return self
