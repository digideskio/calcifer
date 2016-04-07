"""
Premium Command Policy StateT Operators.

These are provided as building blocks for specifying Premium Command Policies
for the purposes of template generation and command validation.

N.B. These considered LOW-LEVEL operators. For command policy specification,
use the operators in `dramafever.premium.commands` and not this module.
"""
from pymonad import List

from dramafever.premium.services.policy.monads import (
    stateT
)


#
# Policy Operators
#

def make_set_value(m):
    def set_value(value):
        """
        Sets the value for the currently scoped policy node. Overwrites
        the node with a LeafPolicyNode
        """
        @stateT(m)
        def for_policy(policy):
            return m.unit(policy.set_value(value))
        return for_policy
    return set_value
set_value = make_set_value(List)


def make_select(m):
    def select(selector, set_path=True):
        """
        Retrieves the policy node at a given selector and optionally
        sets the scope to that selector
        """
        @stateT(m)
        def for_policy(policy):
            return m.unit(policy.select(selector, set_path=set_path))
        return for_policy
    return select
select = make_select(List)


def make_const(m):
    def const(func):
        """
        Given a policy rule, returns a function that ignores its argument
        and simply returns the policy rule.

        (Useful helper for chaining)
        """
        def for_value(_):
            return func
        return for_value
    return const
const = make_const(List)


def make_path(m):
    def path():
        """
        Retrieves the path for the current scope
        """
        @stateT(m)
        def for_policy(policy):
            return m.unit( (policy.path, policy) )
        return for_policy
    return path
path = make_path(List)


def make_set_path(m):
    def set_path(new_path):
        """
        Sets the path for the current scope
        """
        @stateT(m)
        def for_policy(policy):
            return m.unit( policy.set_path(new_path) )
        return for_policy
    return set_path
set_path = make_set_path(List)

def make_define_as(m):
    def define_as(definition):
        """
        Sets the path for the current scope
        """
        @stateT(m)
        def for_policy(policy):
            return m.unit( policy.define_as(definition) )
        return for_policy
    return define_as
define_as = make_define_as(List)

def make_with_value(m):
    def with_value(func):
        """
        Given a function `func(node_value): PolicyRule`, returns a function
        that takes a node and calls `func` with the node's value
        """
        def for_node(node):
            @stateT(m)
            def for_policy(policy):
                return func(node.value)(policy)
            return for_policy
        return for_node
    return with_value
with_value = make_with_value(List)


def make_check(m):
    def check(func):
        """
        Given a function that takes no arguments, returns a
        policy rule that runs the function and returns the result
        and an unchanged policy
        """
        @stateT(m)
        def for_policy(policy):
            return m.unit( (func(), policy) )
        return for_policy
    return check
check = make_check(List)


#
# Control Structures
#

def make_do(m):
    unit = stateT(m).unit
    const = make_const(m)

    def do(*rules):
        """
        Given a list of policy rules, returns a function that discards
        its node value arg and returns a single policy rule that is the
        bound fold of the list.
        """
        op = unit(None)
        for rule in rules:
            op = op >> const(rule)

        return const(op)
    return do
do = make_do(List)


def make_policies(m):
    const = make_const(m)
    path = make_path(m)
    set_path = make_set_path(m)
    unit = stateT(m).unit

    def policies(*rules):
        """
        Given a list of policy rules, returns a single policy rule that
        applies each in turn, keeping scope constant for each. (By resetting
        the path each time)
        """
        def op_step(rule):
            return (
                path() >> (lambda old_path:
                rule >>
                const(set_path(old_path))
            ))

        op = unit(None)
        for rule in rules:
            op = op >> const(op_step(rule))

        return op
    return policies
policies = make_policies(List)


def make_regarding(m):
    const = make_const(m)
    path = make_path(m)
    select = make_select(m)
    set_path = make_set_path(m)
    unit = stateT(m).unit

    def regarding(selector, *rule_funcs):
        """
        Given a selector and a list of functions that generate policy rules,
        returns a single policy rule that, for each rule function:
            1. sets the scope to the selector / retrieves the node there
            3. passes the node to the rule_func to generate a policy rule
            4. applies the policy rule at the new scope

        In addition, regarding checks the current scope and restores it when
        it's done.
        """
        def op_step(rule_func):
            return (
                path() >> (lambda old_path:
                select(selector, set_path=True) >>
                rule_func >>
                const(set_path(old_path)))
            )

        op = unit(None)
        for rule_func in rule_funcs:
            op = op >> const(op_step(rule_func))

        return op

    return regarding
regarding = make_regarding(List)


def make_given(m):
    const = make_const(m)
    path = make_path(m)
    select = make_select(m)
    set_path = make_set_path(m)
    unit = stateT(m).unit

    def given(selector, *rule_funcs):
        """
        Given a selector and a list of functions that generate policy rules,
        returns a single policy rule that, for each rule function:
            1. retrieves the node at selector
            3. passes the node to the rule_func to generate a policy rule
            4. applies the policy rule at the current scope

        In addition, given checks the current scope at the start and restores
        it when it's done.

        (`given` is identical to `regarding` except that the provided
        rule_funcs will run in the pre-existing scope)
        """
        def op_step(rule_func):
            return (
                path() >> (lambda old_path:
                select(selector, set_path=False) >>
                rule_func >>
                const(set_path(old_path)))
            )

        op = unit(None)
        for rule_func in rule_funcs:
            op = op >> const(op_step(rule_func))

        return op

    return given
given = make_given(List)


#
# Non-Determinism Rules
#

def make_fail(m):
    def fail():
        @stateT(m)
        def for_policy(policy):
            return m.mzero()
        return for_policy
    return fail
fail = make_fail(List)


def make_match(m):
    def match(compare_to):
        """
        Given an expected value, selects the currently scoped node and ensures
        it matches expected. If the match results in a new node definition,
        the policy is updated accordingly.

        For non-matches, returns a monadic zero (e.g. if we're building a list
        of policies, this would collapse from [policy] to [])
        """
        @stateT(m)
        def for_policy(policy):
            matches, new_policy = policy.match(compare_to)

            if matches:
                return m.unit( (compare_to, new_policy) )

            return m.mzero()
        return for_policy
    return match
match = make_match(List)


def make_permit_values(m):
    match = make_match(m)
    unit = m.unit

    def permit_values(permitted_values):
        """
        Given a list of allowed values, matches the current policy against
        each, forking the non-deterministic computation.
        """
        @stateT(m)
        def for_policy(policy):
            def for_value(value):
                return unit(policy) >> match(value)

            monad = m.mzero()
            for value in permitted_values:
                monad = monad.mplus(for_value(value))

            return monad
        return for_policy
    return permit_values
permit_values = make_permit_values(List)


def make_attempt(m):
    mzero = m.mzero
    unit = m.unit
    do = make_do(m)

    def attempt(*rules):
        """
        Keeping track of the value and policy it receives,
        if the result of do(*rules) on the policy is mzero,
        then `attempt` returns `unit( (initial_value, initial_policy) )`
        otherwise, `attempt` returns the result of the rules.

        N.B. `attempt` is a Policy Rule *Function*, not just a policy
        rule!
        """
        def for_any(value):
            @stateT(m)
            def for_policy(policy):
                initial = unit( (value, policy) )
                result = do(*rules)(value)(policy)
                if result == mzero():
                    return initial
                return result
            return for_policy
        return for_any
    return attempt
attempt = make_attempt(List)


