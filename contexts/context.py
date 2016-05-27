from dramafever.premium.services.policy.operators import (
    policies, regarding, set_value, permit_values, unit_value,
    select, check, require_value, select, append_value,
    forbid_value, children, each, scope, collect,
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

    def require(self, *args):
        if len(args):
            value = args[0]
        else:
            value = self.value
        subctx = self.named_subctx("require")
        subctx.append(require_value, value).or_error()
        return subctx

    def forbid(self, *args):
        if len(args):
            value = args[0]
        else:
            value = self.value
        subctx = self.named_subctx("forbid")
        subctx.append(forbid_value, value).or_error()
        return subctx

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

    def add_error(self):
        self.append(add_error, {})

    @property
    def last_error(self):
        errors_ctx = self.select("/errors").children()
        idx_ctx = errors_ctx.apply(lambda es: es[-1], errors_ctx.value)
        last_error_ctx = idx_ctx.select(idx_ctx.value)
        return last_error_ctx

    def or_error(self):
        catch_ctx = self.or_catch()

        subctx = catch_ctx.subctx()
        subctx.add_error()
        # prepare error

        # include provided value in error
        provided_value_ctx = subctx.apply(
            lambda true_trace_obj: true_trace_obj['value'],
            catch_ctx.value
        )
        provided_value_ctx.last_error.select("value").set_value(provided_value_ctx.value)

        # include scope
        scope_ctx = subctx.apply(
            lambda true_trace_obj: true_trace_obj['scope'],
            catch_ctx.value
        )
        scope_ctx.last_error.select("scope").set_value(scope_ctx.value)

        # include context frameset itself
        ctxes_ctx = subctx.apply(
            lambda true_trace_obj: true_trace_obj['context'],
            catch_ctx.value
        )
        ctxes_ctx.last_error.select("context").set_value(ctxes_ctx.value)

        return self

    def children(self):
        children_ctx = self.subctx(
           lambda policy_rules: (
                children() >> collect(*policy_rules)
            )
        )
        return children_ctx

    def each(self, **kwargs):
        def with_policy_rules(policy_rules):
            def with_true_children(true_children):
                return each(
                    *policy_rules, **kwargs
                )(true_children)
            return with_true_children

        subctx = self.subctx()
        eachctx = subctx.named_subctx(
            "each",
            with_policy_rules,
            subctx.children()
        )
        return eachctx
