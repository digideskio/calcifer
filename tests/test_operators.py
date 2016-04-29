from django.test import TestCase
from pymonad import Just, List, Maybe

from dramafever.premium.services.policy.monads import (
    Identity, policy_rule_func
)
from dramafever.premium.services.policy.tree import (
    LeafPolicyNode, DictPolicyNode, UnknownPolicyNode, Value
)
from dramafever.premium.services.policy import (
    Partial,
    set_value, with_value,
    check, policies, regarding, given, fail, match, attempt,
    permit_values, define_as, children, each, scope,
)
from dramafever.premium.services.policy import operators


# set up the operators for the Identity and Maybe monads for
# testing
set_valueI = operators.make_set_value(Identity)
policyI = operators.make_policies(Identity)
regardingI = operators.make_regarding(Identity)
givenI = operators.make_given(Identity)
matchI = operators.make_match(Identity)
with_valueI = operators.make_with_value(Identity)

set_valueM = operators.make_set_value(Maybe)
policyM = operators.make_policies(Maybe)
regardingM = operators.make_regarding(Maybe)
givenM = operators.make_given(Maybe)
matchM = operators.make_match(Maybe)
with_valueM = operators.make_with_value(Maybe)

class PolicyTestCase(TestCase):
    def test_select(self):
        policy = DictPolicyNode()
        policy["foo"] = DictPolicyNode()
        policy["foo"]["bar"] = LeafPolicyNode(Value(5))

        item = Partial(policy)

        # select existing item
        path = "/foo/bar"
        node, new_item = item.select(path)
        self.assertEqual(item._root, new_item._root)
        self.assertEqual(LeafPolicyNode(Value(5)), node)
        self.assertEqual(path, new_item._pointer.path)

        # select new item
        path = "/foo/baz"
        value, new_item = item.select(path)
        self.assertNotEqual(item._root, new_item._root)
        self.assertEqual(UnknownPolicyNode(), value)
        self.assertEqual(path, new_item._pointer.path)

        # make sure /foo/bar still exists in new_item
        path = "/foo/bar"
        value, _= new_item.select(path)
        self.assertEqual(LeafPolicyNode(Value(5)), value)

    def test_select_no_set_path(self):
        policy = DictPolicyNode()
        policy["foo"] = DictPolicyNode()
        policy["foo"]["bar"] = LeafPolicyNode(Value(5))

        item = Partial(policy)

        path = "/foo/bar"
        value, new_item = item.select(path, set_path=False)
        self.assertEqual(LeafPolicyNode(Value(5)), value)
        self.assertEqual([], new_item.path)


class PolicyBuilderTestCase(TestCase):
    def test_set_valueI(self):
        func = policyI(set_valueI(5))

        _, item = func(Partial()).getValue()

        value, _ = item.select("")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

    def test_regardingI(self):
        func = policyI(
            regardingI("/foo", set_valueI(5))
        )
        _, item = func(Partial()).getValue()
        value, _ = item.select("/foo")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

        func = policyI(
            regardingI("/fields/foo", set_valueI(5))
        )
        _, item = func(Partial()).getValue()
        value, _ = item.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

    def test_regardingI_multiple(self):
        func = policyI(
            regardingI("/fields/foo", set_valueI(5), set_valueI(6))
        )
        _, item = func(Partial()).getValue()
        value, _ = item.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value(6)), value)

    def test_givenI(self):
        func = policyI(
            regardingI("/fields/foo", set_valueI("foo")),
            regardingI(
                "/fields/bar",
                givenI(
                    "/fields/foo", with_valueI(lambda foo: set_valueI(foo + "bar"))
                )
            )
        )
        _, partial = func(Partial()).getValue()

        foo_node, _ = partial.select("/fields/foo")
        bar_node, _ = partial.select("/fields/bar")
        self.assertEqual("foo", foo_node.value)
        self.assertEqual("foobar", bar_node.value)


    def test_regardingM(self):
        func = policyM(
           regardingM("/fields/foo", set_valueM("foo")),
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("foo")), foo_node)

    def test_policyM_multiple(self):
        func = policyM(
           regardingM("/fields/foo", set_valueM("foo")),
           regardingM("/fields/foo", set_valueM("bar")),
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("bar")), foo_node)

    def test_regardingM_multiple(self):
        func = policyM(
           regardingM(
               "/fields/foo",
               set_valueM("foo"),
               set_valueM("bar")
           )
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("bar")), foo_node)

    def test_givenM(self):
        func = policyM(
            regardingM("/fields/foo", set_valueM("foo")),
            regardingM(
                "/fields/bar",
                givenM(
                    "/fields/foo", with_valueM(lambda foo: set_valueM(foo + "bar"))
                )
            )
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")
        bar_node, _ = partial.select("/fields/bar")
        self.assertEqual("foo", foo_node.value)
        self.assertEqual("foobar", bar_node.value)

    def test_matchM(self):
        func = policyM(
            regardingM("/fields/foo", set_valueM("foo")),
            regardingM(
                "/fields/bar",
                givenM(
                    "/fields/foo", with_valueM(lambda foo: set_valueM(foo + "bar"))
                )
            ),
            regardingM("/fields/bar", matchM("foobar"))
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")
        bar_node, _ = partial.select("/fields/bar")
        self.assertEqual("foo", foo_node.value)
        self.assertEqual("foobar", bar_node.value)


    def test_regarding(self):
        func = policies(
            regarding("/fields/foo", set_value("foo"))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        _, partial = results[0]

        foo_node, _ = partial.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value("foo")), foo_node)

    def test_match(self):
        func = policies(
            regarding("/fields/foo", set_value("foo")),
            regarding(
                "/fields/bar",
                given(
                    "/fields/foo", with_value(lambda foo: set_value(foo + "bar"))
                )
            ),
            regarding("/fields/bar", match("foobar"))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

    def test_match_invalid(self):
        func = policies(
            regarding("/fields/foo", set_value("foo")),
            regarding(
                "/fields/bar",
                given(
                    "/fields/foo", with_value(lambda foo: set_value(foo + "bar"))
                )
            ),
            regarding("/fields/bar", match("barfu"))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(0, len(results))

    def test_permit_values(self):
        # case 1, both values come through
        func = policies(
            regarding("/fields/foo", permit_values(["foo", "bar"])),
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(2, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo", "bar"], values)

        # case 2, one value gets filtered through
        func = policies(
            regarding("/fields/foo", permit_values(["foo", "bar"])),
            regarding("/fields/foo", match("foo"))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo"], values)

        # case 3, this one gets tricky... we can do the match() first!
        func = policies(
            regarding("/fields/foo", match("foo")),
            regarding("/fields/foo", permit_values(["foo", "bar"]))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo"], values)

    def test_attempt(self):
        func = policies(
            regarding("/fields",
                regarding("foo",
                    permit_values(["foo", "bar"]),
                    attempt(
                        match("foo"),
                        set_value("foo_updated")
                    ),
                )
            )
        )

        ps = func( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(2, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo_updated", "bar"], values)

    def test_fail(self):
        func = policies(
            regarding("/fields",
                regarding("foo",
                    permit_values(["foo", "bar"]),
                    fail(),
                )
            )
        )

        ps = func( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(0, len(results))

    def test_check(self):
        def get_policies(value):
            return regarding(
                "/fields/foo",
                (check(lambda: value) >> set_value)
            )

        ps = get_policies(5)( Partial() )
        results = ps.getValue()
        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual([5], values)

        ps = get_policies(1000)( Partial() )
        results = ps.getValue()
        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual([1000], values)

    def test_define_as(self):
        definition = Value(5)

        func = policies(
            regarding("/fields/foo",
                define_as(definition)
            )
        )

        ps = func( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()

        values = [r[1].select("/fields/foo")[0].value for r in results]

        self.assertEqual([5], values)

    def test_regarding_return(self):
        func = regarding("/foo")
        ps = func( Partial.from_obj({"foo": 5}) )

        results = ps.getValue()
        values = [r[0] for r in results]

        self.assertEqual([5], values)

    def test_regarding_scoping(self):
        assertEquals = self.assertEquals
        @policy_rule_func(List)
        def expect_scope(expected="/", msg=None):
            return scope() >> (lambda actual:
                check(lambda: assertEquals(actual, expected, msg=msg))
            )

        func = regarding("",
            expect_scope("/", 0),
            regarding("a", expect_scope("/a", 1)),
            expect_scope("/", 2),
            regarding("b",
                expect_scope("/b", 3),
                regarding("c", expect_scope("/b/c", 4)),
                expect_scope("/b", 5),
            ),
        )

        ps = func( Partial.from_obj({}) )


    def test_children(self):
        func = children()
        ps = func( Partial.from_obj({"foo": 5}) )

        results = ps.getValue()
        values = [r[0] for r in results]

        self.assertEqual([['foo']], values)

    def test_each(self):
        counter = {
            "num": 0
        }
        def increment_set(_):
            counter['num'] += 1
            num = counter['num']
            return set_value(num)

        func = children() >> each(increment_set)
        ps = func( Partial.from_obj({"a": 0, "b": 0, "c": 0}) )

        results = ps.getValue()
        roots = [r[1].root for r in results]

        self.assertEquals(len(roots), 1)
        root = roots[0]
        self.assertIsInstance(root, dict)

        values = root.values()
        values.sort()

        self.assertEquals(values, [1,2,3])

    def test_each_ref(self):
        ref_obj = {"a": 7, "b": 3, "c": -1}
        func = children() >> each(set_value, ref=ref_obj)

        ps = func( Partial.from_obj({"a": 0, "b": 0, "c": 0}) )

        results = ps.getValue()
        roots = [r[1].root for r in results]

        self.assertEquals(len(roots), 1)
        root = roots[0]
        self.assertIsInstance(root, dict)

        self.assertEquals(root, ref_obj)
