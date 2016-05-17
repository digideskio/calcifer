from dramafever.premium.services.policy.operators import (
    policies, regarding, set_value, permit_values, unit_value,
    select, check, require_value, select, append_value,
    forbid_value, get_node, children, each, scope,
)
from dramafever.premium.services.policy.contexts.policies import (
    add_error
)
from dramafever.premium.services.policy.contexts.base import BaseContext


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

    def require(self, value=get_node()):
        subctx = self.named_subctx("require")
        subctx.append(require_value, value).or_error()
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
                        "{}".format(true_scope),
                        *policy_rules
                    )
                )
            ),
            scope
        )
        if name is not None:
            subctx.ctx_name = name

        return subctx

    def select(self, scope):
        return self.scope_subctx(scope, 'select("{}")'.format(scope))

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

    def scope(self):
        self.append(scope())
        return self

    def or_error(self):
        catch_ctx = self.or_catch()
        catch_ctx.append(add_error, catch_ctx.value)
        return self


    def each(self, **kwargs):
        eachctx = self.named_subctx(
            "each",
            lambda policy_rules: (
                children() >>
                each(
                    *policy_rules, **kwargs
                )
            )
        )

        return eachctx
