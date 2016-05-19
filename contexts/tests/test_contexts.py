import random
import logging

from django.test import TestCase

from dramafever.premium.services.tests.utils import run_policy

from dramafever.premium.services.policy.contexts.base import Incomplete
from dramafever.premium.services.policy.contexts import (
    Context
)

from dramafever.premium.services.policy import (
    regarding, set_value, unit,

    asts, PolicyRule
)

logger = logging.getLogger(__name__)

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
        items = ctx.get_finalized_items()
        self.assertEquals(len(items), 1)

        result = run_policy(ctx.finalize(), {"foo": "zebra"})
        self.assertEquals(result['bar'], "zebra")

    def test_require(self):
        ctx = Context()
        ctx.consumer_name.require()

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
        )

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

    def test_each(self):
        ctx = Context(name="root")
        ref_obj = {
            "a": 1,
            "c": 3,
            "d": 4,
        }
        eachctx = ctx.select("/dict").each(ref=ref_obj)
        ref_value = eachctx.value

        eachctx.require(ref_value)

        result = run_policy(ctx.finalize(), {
            "dict": {"a": 0, "b": 0, "c": 0, "d": 0}
        })

        self.assertNotIn("data", result)
        self.assertIn("errors", result)

        errors = result["errors"]

        self.assertEquals(len(errors), 1)
        error = errors[0]
        self.assertEquals(error["scope"], "/dict/b")

    def test_finalize(self):
        ctx = Context(name="root")
        a = ctx.select("/a")
        b = a.select("/b")
        b.set_value(a.value)

        incomplete = b.finalize()
        self.assertIsInstance(incomplete, Incomplete)
        self.assertIn(a.value, incomplete.missing)

        completed = incomplete.complete({a.value: 5})
        self.assertIsInstance(completed, PolicyRule)
        result = run_policy(completed)
        self.assertEquals(result['b'], 5)

    def test_finalize_own_ctx_value(self):
        ctx = Context(name="root")
        a = ctx.select("/a")
        b = a.select("/b")
        b.set_value(b.value)

        completed = b.finalize()
        self.assertIsInstance(completed, PolicyRule)

        result = run_policy(completed, {"b": 5})
        self.assertEquals(result['b'], 5)

        completed = ctx.finalize()
        self.assertIsInstance(completed, PolicyRule)

        result = run_policy(completed, {"b": 5})
        self.assertEquals(result['b'], 5)

    def test_finalize_two_ctx_values(self):
        ctx = Context(name="root")
        a = ctx.select("/a")
        b = a.select("/b")
        c = b.select("/c")
        def func(b, a):
            return set_value(a + b)

        c.append(func, a.value, b.value)

        incomplete = c.finalize()
        self.assertIsInstance(incomplete, Incomplete)
        self.assertIn(a.value, incomplete.missing)
        self.assertIn(b.value, incomplete.missing)

        completed = incomplete.complete({a.value: 5, b.value: 2})
        self.assertIsInstance(completed, PolicyRule)

        result = run_policy(completed)
        self.assertEquals(result['c'], 7)

        # now instead of starting with `c` and supplying 2 values,
        # let's start with `b` and only have to supply one value.
        incomplete = b.finalize()
        self.assertIsInstance(incomplete, Incomplete)
        self.assertIn(a.value, incomplete.missing)
        self.assertNotIn(b.value, incomplete.missing)

        completed = incomplete.complete({a.value: 5})
        self.assertIsInstance(completed, PolicyRule)

        result = run_policy(completed, {"b": 2})
        self.assertEquals(result['c'], 7)

    def test_incomplete_hookup(self):
        ctx = Context(name="root")
        a = ctx.select("/a")
        b = a.select("/b")
        b.set_value(a.value)

        complete = a.finalize()
        self.assertIsInstance(complete, PolicyRule)
        result = run_policy(complete, {"a": 5})
        self.assertEquals(result['b'], 5)

        complete = ctx.finalize()
        self.assertIsInstance(complete, PolicyRule)
        result = run_policy(complete, {"a": 5})
        self.assertEquals(result['b'], 5)

    def test_incomplete_hookup_skipping(self):
        ctx = Context(name="root")
        a = ctx.select("/a")
        b = a.select("/b")
        c = b.select("/c")
        c.set_value(a.value)

        complete = a.finalize()
        self.assertIsInstance(complete, PolicyRule)
        result = run_policy(complete, {"a": 5})
        self.assertEquals(result['c'], 5)

        complete = ctx.finalize()
        self.assertIsInstance(complete, PolicyRule)
        result = run_policy(complete, {"a": 5})
        self.assertEquals(result['c'], 5)

    def test_nesting(self):
        ctx = Context(name="root")

        a = ctx.select("/a")
        b = a.select("/b")

        def f_a(a):
            return regarding("/results/f_a", set_value(a))

        def f_b(b):
            return regarding("/results/f_b", set_value(b))

        b.append(f_a, a.value)
        b.append(f_b, b.value)

        c = b.select("/c")

        def f_ab(a, b):
            return regarding("/results/f_ab", set_value(a+b))

        def f_ac(a, c):
            return regarding("/results/f_ac", set_value(a+c))

        c.append(f_ab, a.value, b.value)
        c.append(f_ac, a.value, c.value)

        result = run_policy(ctx.finalize(), {
            "a": 1,
            "b": 2,
            "c": 4,
        })

        a = result['a']
        b = result['b']
        c = result['c']

        f_a = result['results']['f_a']
        f_b = result['results']['f_b']
        f_ab = result['results']['f_ab']
        f_ac = result['results']['f_ac']

        self.assertEquals(f_a, a)
        self.assertEquals(f_b, b)
        self.assertEquals(f_ab, a+b)
        self.assertEquals(f_ac, a+c)

    def test_append_mixed(self):
        ctx = Context(name="root")

        a = ctx.select("/a")
        b = a.select("/b")

        def with_values(a, b):
            return set_value(a+b)

        b.append(with_values, a.value, unit(2))

        result = run_policy(ctx.finalize(), {"a": 5})
        self.assertEquals(result['b'], 7)

    def test_apply(self):
        ctx = Context(name="root")
        a = ctx.select("/a")
        b = a.select("/b")

        def increment(x):
            return x + 1

        # the value only exists inside the context of the function
        # application
        applied_ctx = b.apply(increment, a.value)
        applied_ctx.set_value(applied_ctx.value)

        result = run_policy(ctx.finalize(), {"a": 5})
        self.assertEquals(result['b'], 6)

        # and just for calisthenics, do it in a different order
        ctx = Context(name="root")
        a = ctx.select("/a")
        applied_ctx = a.apply(increment, a.value)
        b = applied_ctx.select("/b")
        b.set_value(applied_ctx.value)

        result = run_policy(ctx.finalize(), {"a": -3})
        self.assertEquals(result['b'], -2)

    def test_apply_alchemy(self):
        # for our test today, we will be doing some basic alchemy
        material_names = [
            "aqua fortis",
            "glauber's salt",
            "lunar caustic",
            "mosaic gold",
            "plumbago",
            "salt",
            "tin salt",
            "butter of tin",
            "stibnite",
            "naples yellow",
        ]

        # backstory:
        # ~~~~~~~~~~
        #
        # falling asleep last night, you finally figured out how to complete
        # your life's work: discovering the elusive *elixir of life*!
        #
        # and it's only two ingredients! and you have them on hand!
        #
        # ...
        #
        # unfortunately this morning you can't remember which two
        # ingredients it was.
        #
        # you'll know it once you've gotten it, just have to try out
        # all possible mixtures. (should be safe enough, right?)

        forgotten_elixir_of_life = set(random.sample(material_names, 2))

        inventory = _take_alchemical_inventory(material_names)

        discoveries_today = set(["frantic worry", "breakfast"])

        # ok time to go do some arbitrary alchemy!
        #
        # game plan:
        alchemy_ctx = Context()

        # you'll grab one ingredient,
        selected_first_ctx = alchemy_ctx.select("/inventory").each()
        first_substance = selected_first_ctx.value

        # and another,
        selected_second_ctx = selected_first_ctx.select("/inventory").each()
        second_substance = selected_second_ctx.value

        # take them to your advanced scientific mixing equipment,
        workstation_ctx = selected_second_ctx.select("/workstation")

        # (btw this is your advanced scientific procedure that you are
        # 100% certain will tell you what some mixture is)
        def mix(first, second):
            """takes two ingredients and returns the resulting substance"""
            if set([first, second]) == forgotten_elixir_of_life:
                return "elixir of life"
            return "some kind of brown goo"

        # then you'll mix your ingredients...
        mixed_ctx = workstation_ctx.apply(mix,
            first_substance, second_substance
        )
        resulting_mixture = mixed_ctx.value

        # ... and! in today's modern age, scientists now know to record their
        # results!
        mixed_ctx.select("/discoveries").append_value(resulting_mixture)

        # got it? good!
        result = run_policy(
            alchemy_ctx.finalize(),
            {"inventory": inventory, "discoveries": discoveries_today}
        )

        # in a flurry of excitement, i bet you didn't even stop to
        # look at your discoveries as you made them!
        #
        # well, let's see...

        self.assertIn("elixir of life", result["discoveries"])

    def test_apply_dangerous_alchemy(self):
        # nice job! and you even finished in time to go foraging for
        # more ingredients!
        material_names = [
            "aqua fortis",
            "glauber's salt",
            "lunar caustic",
            "mosaic gold",
            "plumbago",
            "salt",
            "tin salt",
            "butter of tin",
            "stibnite",
            "naples yellow",

            # nice find
            "anti-plumbago"
        ]

        inventory = {
            str(idx): name
            for idx, name in enumerate(material_names)
        }

        # but unfortunately, it's the next day, and the same thing
        # has happened to you! except this time it was for your
        # other life's goal: discover the ~elixir of discord~!
        #
        # well, since it was so easy...

        whatever_concoction = set(['some ingredients'])

        discoveries_today = set([])
        should_be_fine = 'overconfidence' not in discoveries_today
        assert should_be_fine

        # doing alchemy la la la
        alchemy_ctx = Context()

        # grabbin' things off shelves
        selected_first_ctx = alchemy_ctx.select("/inventory").each()
        first_substance = selected_first_ctx.value

        selected_second_ctx = selected_first_ctx.select("/inventory").each()
        second_substance = selected_second_ctx.value

        # got our ingredients
        got_ingredients_ctx = selected_second_ctx

        workstation_ctx = got_ingredients_ctx.select("/workstation")

        # mixin' - don't stop to think
        def mix(first, second):
            mixture = set([first, second])
            if mixture == whatever_concoction:
                return 'missing elixir'
            if mixture == set(['plumbago', 'anti-plumbago']):
                return 'concentrated danger'
            return 'more brown goo'

        mixed_ctx = workstation_ctx.apply(mix,
            first_substance, second_substance
        )
        resulting_mixture = mixed_ctx.value

        mixed_ctx.select("/discoveries").append_value(resulting_mixture)

        # wait wait wait!!
        def danger(mixture):
            if mixture == 'concentrated danger':
                return True
            return False

        # we can't have that.
        danger_ctx = mixed_ctx.check(danger,
            resulting_mixture
        )
        danger_ctx.forbid()

        # moral:
        #
        # a strong understanding of policies and processes facilitates a
        # hazard-free lab environment.
        result = run_policy(
            alchemy_ctx.finalize(),
            {"inventory": inventory, "discoveries": discoveries_today}
        )

        self.assertIn("errors", result)
        self.assertTrue(len(result['errors']))


def _take_alchemical_inventory(material_names):
    # implementor's note: this is a dict because ctx.each() does
    # not currently support lists
    inventory = {
        str(idx): name
        for idx, name in enumerate(material_names)
    }
    return inventory
