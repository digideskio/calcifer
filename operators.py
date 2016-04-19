"""
Premium Command Policy StateT Operators.

These are provided as building blocks for specifying Premium Command Policies
for the purposes of template generation and command validation.

N.B. These considered LOW-LEVEL operators. For command policy specification,
use the operators in `dramafever.premium.commands` and not this module.
"""
from pymonad import List

from dramafever.premium.services.policy.monads import (
    policy_rule_func, get_call_repr
)


#
# Policy Operators
#

def make_unit(m):
    @policy_rule_func(m)
    def unit(value):
        """
        Returns a value inside the monad
        """
        def for_partial(partial):
            return m.unit((value, partial))
        return for_partial
    return unit
unit = make_unit(List)


def make_set_value(m):
    @policy_rule_func(m)
    def set_value(value):
        """
        Sets the value for the currently scoped policy node. Overwrites
        the node with a LeafPolicyNode
        """
        def for_partial(partial):
            return m.unit(partial.set_value(value))
        return for_partial
    return set_value
set_value = make_set_value(List)


def make_select(m):
    @policy_rule_func(m)
    def select(selector, set_path=False):
        """
        Retrieves the policy node at a given selector and optionally
        sets the scope to that selector
        """
        def for_partial(partial):
            return m.unit(partial.select(selector, set_path=set_path))
        return for_partial
    return select
select = make_select(List)


def make_const(m):
    @policy_rule_func(m)
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
    @policy_rule_func(m)
    def path():
        """
        Retrieves the path for the current scope
        """
        def for_partial(partial):
            return m.unit( (partial.path, partial) )
        return for_partial
    return path
path = make_path(List)


def make_set_path(m):
    @policy_rule_func(m)
    def set_path(new_path):
        """
        Sets the path for the current scope
        """
        def for_partial(partial):
            return m.unit( partial.set_path(new_path) )
        return for_partial
    return set_path
set_path = make_set_path(List)

def make_define_as(m):
    @policy_rule_func(m)
    def define_as(definition):
        """
        Sets the path for the current scope
        """
        def for_partial(partial):
            return m.unit( partial.define_as(definition) )
        return for_partial
    return define_as
define_as = make_define_as(List)

def make_with_value(m):
    def with_value(func):
        """
        Given a function `func(node_value): PolicyRule`, returns a function
        that takes a node and calls `func` with the node's value
        """
        def for_node(node):
            def for_partial(partial):
                return func(node.value)(partial)
            return for_partial
        return policy_rule_func(
            m, get_call_repr("with_value", func)
        )(for_node)
    return with_value
with_value = make_with_value(List)


def make_check(m):
    @policy_rule_func(m)
    def check(func):
        """
        Given a function that takes no arguments, returns a
        policy rule that runs the function and returns the result
        and an unchanged partial
        """
        def for_partial(partial):
            return m.unit( (func(), partial) )
        return for_partial
    return check
check = make_check(List)


#
# Control Structures
#

def make_do(m):
    unit = make_unit(m)
    const = make_const(m)

    @policy_rule_func(m)
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
    unit = make_unit(m)

    @policy_rule_func(m)
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
    unit = make_unit(m)

    @policy_rule_func(m)
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
    unit = make_unit(m)

    @policy_rule_func(m)
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
    @policy_rule_func(m)
    def fail():
        def for_partial(partial):
            return m.mzero()
        return for_partial
    return fail
fail = make_fail(List)


def make_match(m):
    @policy_rule_func(m)
    def match(compare_to):
        """
        Given an expected value, selects the currently scoped node and ensures
        it matches expected. If the match results in a new node definition,
        the partial is updated accordingly.

        For non-matches, returns a monadic zero (e.g. if we're building a list
        of policies, this would collapse from [partial] to [])
        """
        def for_partial(partial):
            matches, new_partial = partial.match(compare_to)

            if matches:
                return m.unit( (compare_to, new_partial) )

            return m.mzero()
        return for_partial
    return match
match = make_match(List)


def make_permit_values(m):
    match = make_match(m)
    unit = m.unit

    @policy_rule_func(m)
    def permit_values(permitted_values):
        """
        Given a list of allowed values, matches the current partial against
        each, forking the non-deterministic computation.
        """
        def for_partial(partial):
            def for_value(value):
                return unit(partial) >> match(value)

            monad = m.mzero()
            for value in permitted_values:
                monad = monad.mplus(for_value(value))

            return monad
        return for_partial
    return permit_values
permit_values = make_permit_values(List)


def make_attempt(m):
    mzero = m.mzero
    unit = m.unit
    do = make_do(m)

    def attempt(*rules):
        """
        Keeping track of the value and partial it receives,
        if the result of do(*rules) on the partial is mzero,
        then `attempt` returns `unit( (initial_value, initial_policy) )`
        otherwise, `attempt` returns the result of the rules.

        N.B. `attempt` is a Policy Rule *Function*, not just a policy
        rule!
        """
        def for_any(value):
            def for_partial(partial):
                initial = unit( (value, partial) )
                result = do(*rules)(value)(partial)
                if result == mzero():
                    return initial
                return result
            return for_partial
        attempt_rule_func_name = get_call_repr("attempt", *rules)
        return policy_rule_func(m, attempt_rule_func_name)(for_any)
    return attempt
attempt = make_attempt(List)


