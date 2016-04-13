import pytest

from django.test import TestCase
from pymonad import Just, List, Maybe

from dramafever.premium.services.policy.monads import Identity
from dramafever.premium.services.policy.tree import (
    LeafPolicyNode, DictPolicyNode, UnknownPolicyNode, Value
)
from dramafever.premium.services.policy import (
    Partial,
    set_value, select, const, path, set_path, with_value,
    check, do, policies, regarding, given, fail, match, attempt,
    permit_values, define_as
)
from dramafever.premium.services.policy import operators


# set up the operators for the Identity and Maybe monads for
# testing
doI = operators.make_do(Identity)
set_valueI = operators.make_set_value(Identity)
constI = operators.make_const(Identity)
policyI = operators.make_policies(Identity)
regardingI = operators.make_regarding(Identity)
givenI = operators.make_given(Identity)
matchI = operators.make_match(Identity)
with_valueI = operators.make_with_value(Identity)

set_valueM = operators.make_set_value(Maybe)
doM = operators.make_do(Maybe)
constM = operators.make_const(Maybe)
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
            regardingI("/foo", doI(set_valueI(5)))
        )
        _, item = func(Partial()).getValue()
        value, _ = item.select("/foo")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

        func = policyI(
            regardingI("/fields/foo", doI(set_valueI(5)))
        )
        _, item = func(Partial()).getValue()
        value, _ = item.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value(5)), value)

    def test_regardingI_multiple(self):
        func = policyI(
            regardingI("/fields/foo", doI(set_valueI(5), set_valueI(6)))
        )
        _, item = func(Partial()).getValue()
        value, _ = item.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value(6)), value)

    def test_givenI(self):
        func = policyI(
            regardingI("/fields/foo", doI(set_valueI("foo"))),
            regardingI(
                "/fields/bar",
                doI(givenI(
                    "/fields/foo", with_valueI(lambda foo: set_valueI(foo + "bar"))
                ))
            )
        )
        _, policy = func(Partial()).getValue()

        foo, _ = policy.select("/fields/foo")
        bar, _ = policy.select("/fields/bar")
        self.assertEqual("foo", foo.value)
        self.assertEqual("foobar", bar.value)


    def test_regardingM(self):
        func = policyM(
           regardingM("/fields/foo", doM(set_valueM("foo"))),
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, policy = maybe.getValue()
        foo, _ = policy.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("foo")), foo)

    def test_policyM_multiple(self):
        func = policyM(
           regardingM("/fields/foo", doM(set_valueM("foo"))),
           regardingM("/fields/foo", doM(set_valueM("bar"))),
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, policy = maybe.getValue()
        foo, _ = policy.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("bar")), foo)

    def test_regardingM_multiple(self):
        func = policyM(
           regardingM(
               "/fields/foo",
               doM(set_valueM("foo")),
               doM(set_valueM("bar"))
           )
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, policy = maybe.getValue()
        foo, _ = policy.select("/fields/foo")

        self.assertEqual(LeafPolicyNode(Value("bar")), foo)

    def test_givenM(self):
        func = policyM(
            regardingM("/fields/foo", doM(set_valueM("foo"))),
            regardingM(
                "/fields/bar",
                doM(givenM(
                    "/fields/foo", with_valueM(lambda foo: set_valueM(foo + "bar"))
                ))
            )
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, policy = maybe.getValue()
        foo, _ = policy.select("/fields/foo")
        bar, _ = policy.select("/fields/bar")
        self.assertEqual("foo", foo.value)
        self.assertEqual("foobar", bar.value)

    def test_matchM(self):
        func = policyM(
            regardingM("/fields/foo", doM(set_valueM("foo"))),
            regardingM(
                "/fields/bar",
                doM(givenM(
                    "/fields/foo", with_valueM(lambda foo: set_valueM(foo + "bar"))
                ))
            ),
            regardingM("/fields/bar", doM(matchM("foobar")))
        )

        maybe = func( Partial() )
        self.assertTrue(isinstance(maybe, Just))
        _, policy = maybe.getValue()
        foo, _ = policy.select("/fields/foo")
        bar, _ = policy.select("/fields/bar")
        self.assertEqual("foo", foo.value)
        self.assertEqual("foobar", bar.value)


    def test_regarding(self):
        func = policies(
            regarding("/fields/foo", do(set_value("foo")))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        _, policy = results[0]

        foo, _ = policy.select("/fields/foo")
        self.assertEqual(LeafPolicyNode(Value("foo")), foo)

    def test_match(self):
        func = policies(
            regarding("/fields/foo", do(set_value("foo"))),
            regarding(
                "/fields/bar",
                do(given(
                    "/fields/foo", with_value(lambda foo: set_value(foo + "bar"))
                ))
            ),
            regarding("/fields/bar", do(match("foobar")))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

    def test_match_invalid(self):
        func = policies(
            regarding("/fields/foo", do(set_value("foo"))),
            regarding(
                "/fields/bar",
                do(given(
                    "/fields/foo", with_value(lambda foo: set_value(foo + "bar"))
                ))
            ),
            regarding("/fields/bar", do(match("barfu")))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(0, len(results))

    def test_permit_values(self):
        # case 1, both values come through
        func = policies(
            regarding("/fields/foo", do(permit_values(["foo", "bar"]))),
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(2, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo", "bar"], values)

        # case 2, one value gets filtered through
        func = policies(
            regarding("/fields/foo", do(permit_values(["foo", "bar"]))),
            regarding("/fields/foo", do(match("foo")))
        )

        ps = func( Partial() )
        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(1, len(results))

        values = [r[1].select("/fields/foo")[0].value for r in results]
        self.assertEqual(["foo"], values)

        # case 3, this one gets tricky... we can do the match() first!
        func = policies(
            regarding("/fields/foo", do(match("foo"))),
            regarding("/fields/foo", do(permit_values(["foo", "bar"])))
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
                do(regarding("foo",
                    do(permit_values(["foo", "bar"])),
                    attempt(
                        match("foo"),
                        set_value("foo_updated")
                    ),
                )
            ))
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
                do(regarding("foo",
                    do(permit_values(["foo", "bar"])),
                    do(fail()),
                )
            ))
        )

        ps = func( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()
        self.assertEqual(0, len(results))

    def test_check(self):
        def get_policies(value):
            return regarding(
                "/fields/foo",
                do(check(lambda: value) >> set_value)
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
                do(define_as(definition))
            )
        )

        ps = func( Partial() )

        self.assertTrue(isinstance(ps, List))

        results = ps.getValue()

        values = [r[1].select("/fields/foo")[0].value for r in results]

        self.assertEqual([5], values)
