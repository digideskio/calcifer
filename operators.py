"""
Premium Command Policy StateT Operators.

These are provided as building blocks for specifying Premium Command Policies
for the purposes of template generation and command validation.

N.B. These considered LOW-LEVEL operators. For command policy specification,
use the operators in `dramafever.premium.commands` and not this module.
"""
from pymonad import List

from dramafever.premium.services.policy.monads import (
    policy_rule_func, get_call_repr,

    PolicyRule
)


#
# Partial Operators
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


def make_unit_value(m):
    @policy_rule_func(m)
    def unit_value(node):
        """
        Given a node (often returned as monadic result), return
        the value for the node.
        """
        def for_partial(partial):
            if hasattr(node, 'value'):
                return m.unit((node.value, partial))
            else:
                return m.unit((None, partial))
        return for_partial
    return unit_value
unit_value = make_unit_value(List)


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


def make_scope(m):
    @policy_rule_func(m)
    def scope():
        """
        Retrieves the selector for the current scope
        """
        def for_partial(partial):
            return m.unit( (partial.scope, partial) )
        return for_partial
    return scope
scope = make_scope(List)


def make_get_node(m):
    @policy_rule_func(m)
    def get_node():
        """
        Retrieves the node at the current pointer
        """
        def for_partial(partial):
            return m.unit( partial.select("") )
        return for_partial
    return get_node
get_node = make_get_node(List)


def make_get_value(m):
    get_node = make_get_node(m)
    unit_value = make_unit_value(m)

    @policy_rule_func(m)
    def get_value():
        """
        Retrieves the value for the node at the current pointer
        """
        return get_node() >> unit_value
    return get_value
get_value = make_get_value(List)


def make_append_value(m):
    get_value = make_get_value(m)
    set_value = make_set_value(m)

    @policy_rule_func(m)
    def append_value(value):
        """
        Gets the value at the current node, and, assuming it to be a list,
        appends `value`
        """
        return get_value() >> (lambda values: set_value(values + [value]))
    return append_value
append_value = make_append_value(List)


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
            new_definition, new_partial = partial.define_as(definition)
            if new_definition is None:
                return m.mzero()
            return m.unit( (new_definition, new_partial) )
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

def make_policies(m):
    unit = make_unit(m)

    @policy_rule_func(m)
    def policies(*rules):
        """
        Given a list of policy rules, returns a single policy rule that
        applies each in turn, keeping scope constant for each. (By resetting
        the path each time)
        """
        @policy_rule_func(m)
        def policy_step(rule):
            def for_partial(partial):
                original_scope = partial.scope
                if isinstance(rule, PolicyRule):
                    results = rule(partial)
                else:
                    results = rule(None)(partial)

                def for_result(result):
                    _, partial = result
                    _, rescoped_partial = partial.select(
                        original_scope, set_path=True
                    )
                    return None, rescoped_partial

                return results.fmap(for_result)
            return for_partial

        op = unit(None)
        for rule in rules:
            op = op >> policy_step(rule)

        return op
    return policies
policies = make_policies(List)


def make_regarding(m):
    select = make_select(m)
    unit = make_unit(m)
    unit_value = make_unit_value(m)

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
        @policy_rule_func(m)
        def regarding_step(rule_func):
            def for_partial(partial):
                original_scope = partial.scope
                node, inner_partial = partial.select(selector, set_path=True)
                value = node.value
                if not value:
                    value = node
                if isinstance(rule_func, PolicyRule):
                    results = rule_func(inner_partial)
                else:
                    results = rule_func(value)(inner_partial)
                def for_result(result):
                    _, partial = result
                    _, rescoped_partial = partial.select(
                        original_scope, set_path=True
                    )
                    return value, rescoped_partial

                return results.fmap(for_result)
            return for_partial

        if rule_funcs:
            op = unit(None)
            for rule_func in rule_funcs:
                op = op >> regarding_step(rule_func)
        else:
            op = select(selector, set_path=False) >> unit_value

        return op

    return regarding
regarding = make_regarding(List)


def make_given(m):
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
        @policy_rule_func(m)
        def given_step(rule_func):
            return (
                path() >> (lambda old_path:
                select(selector, set_path=False) >>
                rule_func >>
                set_path(old_path))
            )

        op = unit(None)
        for rule_func in rule_funcs:
            op = op >> given_step(rule_func)

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
    unit = make_unit(m)

    def attempt(*rules, **kwargs):
        """
        Keeping track of the value and partial it receives,
        if the result of *rules on the partial is mzero,
        then `attempt` returns `unit( (initial_value, initial_policy) )`
        otherwise, `attempt` returns the result of the rules.

        Accepts a policy rule function as kwarg `catch=` which can be
        applied instead of simply "not failing"
        """
        def for_any(value):
            def for_partial(partial):
                op = unit(value)
                initial = op(partial)
                for rule in rules:
                    op = op >> rule
                result = op(partial)

                if result == mzero():
                    if 'catch' in kwargs:
                        alternative = (unit(value) >> kwargs['catch'])(partial)
                        return alternative
                    return initial
                return result
            return for_partial
        attempt_rule_func_name = get_call_repr("attempt", *rules, **kwargs)
        return policy_rule_func(m, attempt_rule_func_name)(for_any)
    return attempt
attempt = make_attempt(List)


#
# Context Operators
#

def make_push_context(m):
    @policy_rule_func(m)
    def push_context(context):
        """
        Add an additional context to the stack for the partial
        """
        def for_partial(partial):
            return m.unit( partial.push_context(context) )
        return for_partial
    return push_context
push_context = make_push_context(List)


def make_pop_context(m):
    @policy_rule_func(m)
    def pop_context(passthru):
        """
        Pop the partial's context stack, returning whatever
        value it was called with.
        """
        def for_partial(partial):
            _, new_partial = partial.pop_context()

            return m.unit( (passthru, new_partial) )
        return for_partial
    return pop_context
pop_context = make_pop_context(List)


def make_wrap_context(m):
    push_context = make_push_context(m)
    pop_context = make_pop_context(m)

    @policy_rule_func(m)
    def wrap_context(context, op):
        """
        Run some operator inside some context
        """
        return push_context(context) >> op >> pop_context

    return wrap_context
wrap_context = make_wrap_context(List)


def make_require_value(m):
    get_node = make_get_node(m)

    @policy_rule_func(m)
    def require_value():
        """
        Returns an mzero (empty list, e.g.) if the provided node
        is missing a value

        For instance:
            select("/does/not/exist") >> require_value
        returns []
        """
        def for_node(node):
            def for_partial(partial):
                if node.value is None:
                    return m.mzero()
                return m.unit( (None, partial) )
            return for_partial
        return get_node() >> for_node
    return require_value
require_value = make_require_value(List)


def make_forbid_value(m):
    get_node = make_get_node(m)

    @policy_rule_func(m)
    def forbid_value():
        """
        Returns an mzero (empty list, e.g.) if the provided node
        is missing a value

        For instance:
            select("/does/not/exist") >> forbid_value
        returns []
        """
        def for_node(node):
            def for_partial(partial):
                if node.value is not None:
                    return m.mzero()
                return m.unit( (None, partial) )
            return for_partial
        return get_node() >> for_node
    return forbid_value
forbid_value = make_forbid_value(List)


def make_unless_errors(m):
    @policy_rule_func(m)
    def unless_errors(*rules):
        def for_partial(partial):
            errors = partial.root.get('errors', None)
            if errors:
                return m.unit( (None, partial) )
            return policies(*rules)(partial)
        return for_partial
    return unless_errors
unless_errors = make_unless_errors(List)


def make_trace(m):
    scope = make_scope(m)
    get_value = make_get_value(m)
    select = make_select(m)
    unit = make_unit(m)
    unit_value = make_unit_value(m)

    @policy_rule_func(m)
    def trace():
        """
        Collates the current scope, the current node's value,
        and the current policy context and returns it as a dict
        """
        return scope() >> (
            lambda scope: (
                get_value() >> (
                    lambda value: (
                        select("/context") >> unit_value >> (
                            lambda context: (
                                unit({
                                    "scope": scope,
                                    "context": context,
                                    "value": value
                                })
                            )
                        )
                    )
                )
            )
        )
    return trace
trace = make_trace(List)
