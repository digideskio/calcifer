import unittest
from unittest import TestCase

from pymonad import Just, List, Maybe

from calcifer.monads import (
    Identity, policy_rule_func
)
from calcifer.tree import (
    LeafPolicyNode, DictPolicyNode, UnknownPolicyNode, Value
)
from calcifer import (
    Partial,
    set_value, select, check, policies, regarding, fail, match, attempt,
    permit_values, define_as, children, each, scope,
)
from calcifer import operators


# set up the operators for the Identity and Maybe monads for
# testing
set_valueI = operators.make_set_value(Identity)
policyI = operators.make_policies(Identity)
regardingI = operators.make_regarding(Identity)
selectI = operators.make_select(Identity)
matchI = operators.make_match(Identity)

set_valueM = operators.make_set_value(Maybe)
policyM = operators.make_policies(Maybe)
regardingM = operators.make_regarding(Maybe)
selectM = operators.make_select(Maybe)
matchM = operators.make_match(Maybe)

class PolicyTestCase(TestCase):
    def test_select(self):
        policy = DictPolicyNode()
        foo_node = DictPolicyNode()
        bar_node = LeafPolicyNode(Value(5))

        foo_node['bar'] = bar_node
        policy["foo"] = foo_node

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
        foo_node = DictPolicyNode()
        bar_node = LeafPolicyNode(Value(5))
        foo_node["bar"] = bar_node
        policy["foo"] = foo_node

        item = Partial(policy)

        path = "/foo/bar"
        value, new_item = item.select(path, set_path=False)
        self.assertEqual(LeafPolicyNode(Value(5)), value)
        self.assertEqual([], new_item.path)


class PolicyBuilderTestCase(TestCase):
    def test_set_valueI(self):
        rule = policyI(set_valueI(5))

        _, item = rule.run(Partial()).getValue()

        value, _ = item.select("")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

    def test_regardingI(self):
        rule = policyI(
            regardingI("/foo", set_valueI(5))
        )
        _, item = rule.run(Partial()).getValue()
        value, _ = item.select("/foo")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

        rule = policyI(
            regardingI("/fields/foo", set_valueI(5))
        )
        _, item = rule.run(Partial()).getValue()
        value, _ = item.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

    def test_regardingI_multiple(self):
        rule = policyI(
            regardingI("/fields/foo", set_valueI(5), set_valueI(6))
        )
        _, item = rule.run(Partial()).getValue()
        value, _ = item.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value(6)), value)

    def test_regardingM(self):
        rule = policyM(
            regardingM("/fields/foo", set_valueM("foo")),
        )

        maybe = rule.run( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("foo")), foo_node)

    def test_policyM_multiple(self):
        rule = policyM(
            regardingM("/fields/foo", set_valueM("foo")),
            regardingM("/fields/foo", set_valueM("bar")),
        )

        maybe = rule.run( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("bar")), foo_node)

    def test_regardingM_multiple(self):
        rule = policyM(
            regardingM("/fields/foo", set_valueM("foo"), set_valueM("bar"))
        )

        maybe = rule.run( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("bar")), foo_node)

    def test_matchM(self):
        rule = policyM(
            regardingM("/fields/foo", set_valueM("foo")),
            regardingM(
                "/fields/bar",
                selectM("/fields/foo") >> (
                    lambda foo: set_valueM(foo.value + "bar")
                )
            ),
            regardingM("/fields/bar", matchM("foobar"))
        )

        maybe = rule.run( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, partial = maybe.getValue()
        foo_node, _ = partial.select("/fields/foo")
        bar_node, _ = partial.select("/fields/bar")
        self.assertEqual("foo", foo_node.value)
        self.assertEqual("foobar", bar_node.value)

    def test_regarding(self):
        rule = policies(
            regarding("/fields/foo", set_value("foo"))
        )

        ps = rule.run( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        _, partial = results[0]

        foo_node, _ = partial.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value("foo")), foo_node)

    def test_match(self):
        rule = policies(
            regarding("/fields/foo", set_value("foo")),
            regarding(
                "/fields/bar",
                select("/fields/foo") >> (
                    lambda foo: set_value(foo.value + "bar")
                )
            ),
            regarding("/fields/bar", match("foobar"))
        )

        ps = rule.run( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

    def test_match_invalid(self):
        rule = policies(
            regarding("/fields/foo", set_value("foo")),
            regarding(
                "/fields/bar",
                select("/fields/foo") >> (
                    lambda foo: set_value(foo.value + "bar")
                )
            ),
            regarding("/fields/bar", match("barfu"))
        )

        ps = rule.run( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(0, len(results))

    def test_permit_values(self):
        # case 1, both values come through
        rule = policies(
            regarding("/fields/foo", permit_values(["foo", "bar"])),
        )

        ps = rule.run( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(2, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo", "bar"], values)

        # case 2, one value gets filtered through
        rule = policies(
            regarding("/fields/foo", permit_values(["foo", "bar"])),
            regarding("/fields/foo", match("foo"))
        )

        ps = rule.run( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo"], values)

        # case 3, this one gets tricky... we can do the match() first!
        rule = policies(
            regarding("/fields/foo", match("foo")),
            regarding("/fields/foo", permit_values(["foo", "bar"]))
        )

        ps = rule.run( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo"], values)

    def test_attempt(self):
        rule = policies(
            regarding(
                "/fields",
                regarding(
                    "foo",
                    permit_values(["foo", "bar"]),
                    attempt(
                        match("foo"),
                        set_value("foo_updated")
                    ),
                )
            )
        )

        ps = rule.run( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(2, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo_updated", "bar"], values)

    def test_fail(self):
        rule = policies(
            regarding(
                "/fields",
                regarding(
                    "foo",
                    permit_values(["foo", "bar"]),
                    fail(),
                )
            )
        )

        ps = rule.run( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(0, len(results))

    def test_check(self):
        def get_policies(value):
            return regarding(
                "/fields/foo",
                (check(lambda: value) >> set_value)
            )

        ps = get_policies(5).run( Partial() )
        results = ps.getValue()
        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual([5], values)

        ps = get_policies(1000).run( Partial() )
        results = ps.getValue()
        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual([1000], values)

    def test_define_as(self):
        definition = Value(5)

        rule = policies(
            regarding(
                "/fields/foo",
                define_as(definition)
            )
        )

        ps = rule.run( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()

        values = [r[1].select("/fields/foo")[0].value for r in results]

        self.assertEqual([5], values)

    def test_regarding_return(self):
        rule = regarding("/foo")
        ps = rule.run( Partial.from_obj({"foo": 5}) )

        results = ps.getValue()
        values = [r[0] for r in results]

        self.assertEqual([5], values)

    def test_regarding_scoping(self):
        assertEqual = self.assertEqual
        @policy_rule_func(List)
        def expect_scope(expected="/", msg=None):
            def for_actual(actual):
                def checker():
                    return assertEqual(actual, expected, msg)
                return check(checker)

            return scope() >> for_actual

        rule = regarding(
            "",
            expect_scope("/", 0),
            regarding("a", expect_scope("/a", 1)),
            expect_scope("/", 2),
            regarding(
                "b",
                expect_scope("/b", 3),
                regarding("c", expect_scope("/b/c", 4)),
                expect_scope("/b", 5),
            ),
        )

        rule.run( Partial.from_obj({}) )


    def test_children(self):
        rule = children()
        ps = rule.run( Partial.from_obj({"foo": 5}) )

        results = ps.getValue()
        values = [r[0] for r in results]

        self.assertEqual([['foo']], values)

    def test_children_list(self):
        rule = children()
        ps = rule.run( Partial.from_obj([9,4,7,1,1]) )

        results = ps.getValue()
        values = [r[0] for r in results]

        self.assertEqual([["0", "1", "2", "3", "4"]], values)

    def test_each(self):
        counter = {
            "num": 0
        }
        def increment_set(_):
            counter['num'] += 1
            num = counter['num']
            return set_value(num)

        rule = children() >> each(increment_set)
        ps = rule.run( Partial.from_obj({"a": 0, "b": 0, "c": 0}) )

        results = ps.getValue()
        roots = [r[1].root for r in results]

        self.assertEqual(len(roots), 1)
        root = roots[0]
        self.assertIsInstance(root, dict)

        values = sorted(root.values())

        self.assertEqual(values, [1,2,3])

    def test_each_list(self):
        def increment(value):
            return set_value(value+1)

        rule = children() >> each(increment)
        ps = rule.run( Partial.from_obj([2, 5, 1]) )

        results = ps.getValue()
        roots = [r[1].root for r in results]

        self.assertEqual(len(roots), 1)
        values = roots[0]
        self.assertIsInstance(values, list)

        self.assertEqual(values, [3,6,2])

    def test_each_ref(self):
        ref_obj = {"a": 7, "b": 3, "c": -1}
        rule = children() >> each(set_value, ref=ref_obj)

        ps = rule.run( Partial.from_obj({"a": 0, "b": 0, "c": 0}) )

        results = ps.getValue()
        roots = [r[1].root for r in results]

        self.assertEqual(len(roots), 1)
        root = roots[0]
        self.assertIsInstance(root, dict)

        self.assertEqual(root, ref_obj)


if __name__ == '__main__':
    unittest.main()
