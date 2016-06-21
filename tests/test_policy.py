# pylint: disable=no-self-argument
import unittest
from unittest import TestCase

from calcifer.partial import Partial

from calcifer.policy import BasePolicy


class PolicyProviderTestCase(TestCase):
    def test_decorator(self):
        class HasPolicy(object):
            class Policy(BasePolicy):
                pass

            @Policy
            def a_policy(ctx):
                ctx.select("/sender").require()

        policy_haver = HasPolicy()

        a_policy = policy_haver.a_policy

        self.assertIsInstance(a_policy, HasPolicy.Policy)

        results = a_policy.run({"sender": "someone"})
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Partial)

    def test_resolve(self):
        class HasPolicy(object):
            class Policy(BasePolicy):
                def resolve(self, policy_final):
                     return policy_final.root['somenode']

            @Policy
            def a_policy(ctx):
                ctx.select("/sender").require()

        policy_haver = HasPolicy()
        a_policy = policy_haver.a_policy
        results = a_policy.run({
            "sender": "someone",
            "somenode": "bajillion"
        })
        self.assertEqual(results[0], "bajillion")

    def test_includes(self):
        class HasPolicy(object):
            class Policy(BasePolicy):
                @staticmethod
                def resolve(final):
                    return final.root['list']

            @Policy(includes=['b', 'c'])
            def a(ctx):
                ctx.select("/list").append_value(1)

            @Policy
            def b(ctx):
                ctx.select("/list").append_value(2)

            @Policy
            def c(ctx):
                ctx.select("/list").append_value(3)


        policy_haver = HasPolicy()
        a_policy = policy_haver.a
        results = a_policy.run({
            "list": []
        })
        self.assertEqual(results[0], [1,2,3])


if __name__ == '__main__':
    unittest.main()
