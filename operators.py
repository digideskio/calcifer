"""
Premium Command Policy StateT Operators.

These are provided as building blocks for specifying Premium Command Policies
for the purposes of template generation and command validation.

N.B. These considered LOW-LEVEL operators. For command policy specification,
use the operators in `dramafever.premium.commands` and not this module.
"""
from pymonad import List

from dramafever.premium.services.policy.tree import PolicyNode
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


def make_children(m):
    @policy_rule_func(m)
    def children():
        def for_partial(partial):
            node, _ = partial.select("")
            if not hasattr(node, 'keys'):
                return m.unit( ([], partial) )

            return m.unit( (node.keys, partial) )
        return for_partial
    return children
children = make_children(List)


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
        def append_to(collection):
            if isinstance(collection, list):
                return collection + [value]
            elif isinstance(collection, (set, frozenset)):
                return collection | frozenset([value])
            else:
                raise NotImplementedError

        return get_value() >> (lambda collection:
            set_value(append_to(collection))
        )
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
                return func(node.value).run(partial)
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

def make_collect(m):
    unit = make_unit(m)
    def collect(*rule_funcs):
        """
        Given a list of policy rule functions, returns a single policy rule
        func that accepts some value, provides that to each function,
        resetting the scope each time.
        """
        def for_incoming_value(incoming_value):
            def for_initial_partial(initial_partial):
                initial_scope = initial_partial.scope

                m_results = m.unit( (incoming_value, initial_partial) )
                def for_rule_func(rule_func):
                    def for_m_result(m_result):
                        _, partial = m_result
                        _, scoped_partial = partial.select(
                            initial_scope, set_path=True
                        )

                        rule = unit(incoming_value) >> rule_func
                        m_results = rule.run(scoped_partial)
                        return m_results
                    return for_m_result

                for rule_func in rule_funcs:
                    for_m_result = for_rule_func(rule_func)
                    m_results = m_results >> for_m_result
                return m_results
            return for_initial_partial
        collect_func_name = get_call_repr('collect', *rule_funcs)
        return policy_rule_func(m, collect_func_name)(for_incoming_value)
    return collect
collect = make_collect(List)


def make_policies(m):
    unit = make_unit(m)

    @policy_rule_func(m)
    def policies(*rule_funcs):
        """
        Given a list of policy rules, returns a single policy rule that
        applies each in turn, keeping scope constant for each. (By resetting
        the path each time)
        """
        def for_initial_partial(initial_partial):
            initial_scope = initial_partial.scope

            m_results = m.unit( (None, initial_partial) )
            def for_rule_func(rule_func):
                def for_m_result(m_result):
                    _, partial = m_result
                    _, scoped_partial = partial.select(
                        initial_scope, set_path=True
                    )

                    rule = unit(None) >> rule_func
                    m_results = rule.run(scoped_partial)
                    return m_results
                return for_m_result

            for rule_func in rule_funcs:
                for_m_result = for_rule_func(rule_func)
                m_results = m_results >> for_m_result
            return m_results
        return for_initial_partial
    return policies
policies = make_policies(List)


def make_regarding(m):
    policies = make_policies(m)
    select = make_select(m)
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
                    results = rule_func.run(inner_partial)
                else:
                    results = rule_func(value).run(inner_partial)
                def for_result(result):
                    _, partial = result
                    _, rescoped_partial = partial.select(
                        original_scope, set_path=True
                    )
                    return value, rescoped_partial

                return results.fmap(for_result)
            return for_partial

        if rule_funcs:
            op = policies(*[regarding_step(rule_func) for rule_func in rule_funcs])
        else:
            op = select(selector, set_path=False) >> unit_value

        return op

    return regarding
regarding = make_regarding(List)


def make_each(m):
    unit = make_unit(m)
    def each(*rule_funcs, **kwargs):
        """
        `each(rule_func)` is a policy rule function that accepts a
        dictionary and calls `rule_func(value)` successively, with the
        partial scope set to the key.

        `each` optionally takes a named argument `ref=dict()` to provide
        a built-in lookup for some reference dictionary. If ref is
        provided, `rule_func(ref[key])` is called instead.
        """
        ref_obj = kwargs.get('ref')

        def for_keys(keys):
            @policy_rule_func(m)
            def each_step(key, rule_func):
                if ref_obj is not None:
                    value = ref_obj.get(key)
                    return (
                        regarding(key, unit(value) >> rule_func)
                    )
                return regarding(key, rule_func)

            steps = [
                each_step(key, rule_func)
                for rule_func in rule_funcs
                for key in keys
            ]
            return regarding("", *steps)

        each_rule_func_name = get_call_repr("each", *rule_funcs, **kwargs)
        return policy_rule_func(m, each_rule_func_name)(for_keys)
    return each
each = make_each(List)


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

    @policy_rule_func(m)
    def permit_values(permitted_values):
        """
        Given a list of allowed values, matches the current partial against
        each, forking the non-deterministic computation.
        """
        def for_partial(partial):
            def for_value(value):
                rule = match(value)
                return rule.run(partial)

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
    collect = make_collect(m)

    def attempt(*rules, **kwargs):
        """
        Keeping track of the value and partial it receives,
        if the result of *rules on the partial is mzero,
        then `attempt` returns `unit( (initial_value, initial_policy) )`
        otherwise, `attempt` returns the result of the rules.

        Accepts a policy rule function as kwarg `catch=` which can be
        applied instead of simply "not failing"
        """
        def for_value(value):
            def for_partial(initial_partial):
                op = unit(value) >> collect(*rules)
                result = op.run(initial_partial)

                if result == mzero():
                    if 'catch' in kwargs:
                        alternative = (unit(value) >> kwargs['catch']).run(
                            initial_partial
                        )
                        return alternative
                    return m.unit( (value, initial_partial) )
                return result
            return for_partial
        attempt_rule_func_name = get_call_repr("attempt", *rules, **kwargs)
        return policy_rule_func(m, attempt_rule_func_name)(for_value)
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
    @policy_rule_func(m)
    def require_value(node):
        """
        Returns an mzero (empty list, e.g.) if the provided node
        is missing a value
        For instance:
            select("/does/not/exist") >> require_value
        returns []
        """
        def for_partial(partial):
            if isinstance(node, PolicyNode):
                if node.value is None:
                    return m.mzero()
            if node is None:
                return m.mzero()
            return m.unit( (None, partial) )
        return for_partial
    return require_value
require_value = make_require_value(List)


def make_forbid_value(m):
    @policy_rule_func(m)
    def forbid_value(node):
        """
        Returns an mzero (empty list, e.g.) if the provided node
        is missing a value

        For instance:
            select("/does/not/exist") >> forbid_value
        returns []
        """
        def for_partial(partial):
            if isinstance(node, PolicyNode):
                if node.value is None:
                    return m.unit( (None, partial) )
            if node is None:
                return m.unit( (None, partial) )
            return m.mzero()
        return for_partial
    return forbid_value
forbid_value = make_forbid_value(List)


def make_unless_errors(m):
    policies = make_policies(m)
    @policy_rule_func(m)
    def unless_errors(*rules):
        def for_partial(partial):
            errors = partial.root.get('errors', None)
            if errors:
                return m.unit( (None, partial) )
            return policies(*rules).run(partial)
        return for_partial
    return unless_errors
unless_errors = make_unless_errors(List)


def make_trace(m):
    unit = make_unit(m)
    policies = make_policies(m)

    @policy_rule_func(m)
    def trace(*rule_funcs):
        """
        Collates the current scope, the current node's value,
        and the current policy context and returns it as a dict
        """
        @policy_rule_func(m)
        def trace_step(rule_func):
            def for_partial(partial):
                # collect information
                scope = partial.scope
                value = partial.scope_value
                context_node, _ = partial.select("/context")
                context = context_node.value

                # build obj that gets passed to rule_func
                trace_obj = {
                    "scope": scope,
                    "value": value,
                    "context": context,
                }

                # run rule_func
                if isinstance(rule_func, PolicyRule):
                    rule = rule_func
                else:
                    rule = rule_func(trace_obj)
                results = rule.run(partial)

                # rescope partial for next step
                def for_result(result):
                    value, partial = result
                    _, rescoped_partial = partial.select(
                        scope, set_path=True
                    )
                    return value, rescoped_partial

                return results.fmap(for_result)
            return for_partial

        if not rule_funcs:
            rule_funcs = [unit]

        op = policies(*[trace_step(rule_func) for rule_func in rule_funcs])

        return op
    return trace
trace = make_trace(List)
