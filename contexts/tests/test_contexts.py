from django.test import TestCase

from dramafever.premium.services.tests.utils import run_policy

from dramafever.premium.services.policy.contexts import (
    Context
)

from dramafever.premium.services.policy import (
    regarding, set_value, unit,

    asts
)

class ContextTestCase(TestCase):
    def test_append_policy(self):
        ctx = Context()
        policy = regarding('/foo', set_value(5))
        ctx.append(policy)
        policy = ctx.finalize()

        result = run_policy(policy)

        self.assertEquals(result['foo'], 5)

    def test_append_function(self):
        ctx = Context()
        value = unit(5)

        def with_value(value):
            return regarding(
                '/foo',
                set_value(value)
            )

        ctx.append(with_value, value)
        policy = ctx.finalize()

        result = run_policy(policy)
        self.assertEquals(result['foo'], 5)

    def test_subctx_policy(self):
        ctx = Context()

        subctx = ctx.subctx(
            lambda policy_rules: regarding('/foo', *policy_rules)
        )

        subctx.append(
            set_value(5)
        )

        result = run_policy(ctx.finalize())
        self.assertEquals(result['foo'], 5)

    def test_subctx_noop_policy(self):
        ctx = Context()

        foo_ctx_value = ctx.subctx(
            lambda policy_rules: regarding('/foo', *policy_rules)
        )

        def with_foo(foo_value):
            return regarding('/bar', set_value(foo_value))

        ctx.append(with_foo, foo_ctx_value)

        # foo is only used as a value - never being applied policy
        # rules itself.
        # ctx therefore should only have 1 policy, the `with_foo`
        # function above that just sets {foo: *, bar: foo}
        items = ctx.finalized_items
        self.assertEquals(len(items), 1)

        result = run_policy(ctx.finalize(), {"foo": "zebra"})
        self.assertEquals(result['bar'], "zebra")

    def test_or_error(self):
        ctx = Context()
        ctx.consumer_name.require().or_error()

        obj = {
            "sender": {
            },
            "errors": [],
            "context": [],
        }

        result = run_policy(ctx.finalize(), obj)

        error = result["errors"][0]

        self.assertEquals(error["scope"], "/sender/consumer_name")
        self.assertEquals(error["value"], None)
        self.assertEquals(len(error["context"]), 2)

        expected_context_names = ["consumer_name", "require"]
        actual_context_names = [frame.name for frame in error["context"]]
        self.assertEquals(expected_context_names, actual_context_names)

        policy_asts = [frame.policy_ast for frame in error["context"]]

        for ast in policy_asts:
            self.assertIsInstance(ast, asts.Node)


    def test_whitelist_values(self):
        ctx = Context()
        ctx.consumer_name.whitelist_values(
            ["ios", "android"]
        ).or_error()

        obj = {
            "sender": {
                "consumer_name": "www"
            },
            "errors": [],
            "context": [],
        }
        result = run_policy(ctx.finalize(), obj)

        error = result["errors"][0]

        error_context_names = [frame.name for frame in error['context']]
        self.assertIn("whitelist_values", error_context_names)

