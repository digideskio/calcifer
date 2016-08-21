"""
`calcifer.monads` module

Mainly this module provides an implementation of the StateT monad transformer.
The StateT monad is used for non-deterministic generation of templates for
commands.

Some background: the State monad models a function:
    runState(initial_state) -> (computation_result_value, new_state)
that runs a stateful operation on some initial state. The usage of the State
monad and not some other mechanism means that stateful operations can be
chained together in a semantically rich way. (For examples of this chaining,
see the .operators module)

StateT describes *non-deterministic* stateful operations - operations that may
only possibly return a new state, or operations that return more than one
possible new state, etc.

For commands in this system, the StateT monad is used to specifically
transform the List monad: clients may be allowed to run commands in more than
one way, and thus, the command policy for a given request may indeed return
any number of templates, including zero. This is realized as:
    runStateT(initial_state) -> [(computation_result_value, new_state)]
"""
from abc import ABCMeta
import copy
import inspect
import logging
from pymonad import Monad

from calcifer import asts
from calcifer.asts import get_call_repr # pylint: disable=unused-import

logger = logging.getLogger(__name__)


def stateT(m):
    class StateT(Monad):
        """
        The StateT monad transformer runs stateful computations over an
        internal monad. This allows non-deterministic policy code to
        generate more than one template at a time (StateT over a List).

        Helpful information may be found at:
        https://en.wikibooks.org/wiki/Haskell/Monad_transformers
        """
        @classmethod
        def unit(cls, value):
            return cls(lambda state: m.unit( (value, state) ))

        def bind(self, function):
            @StateT
            def newState(state):
                def for_state_result(result):
                    # before state transition
                    value, state = result

                    # after state transition
                    m_new_result = function(value).run(state)

                    return m_new_result

                return self.run(state) >> for_state_result
            return newState

        @property
        def run(self):
            return self.value

        def fmap(self, function):
            return super(StateT, self).fmap(function)

        def amap(self, function):
            return super(StateT, self).amap(function)

    return StateT


class Identity(Monad):
    """
    The Identity monad is provided here to accompany tests on simple state
    mechanisms that do not exhibit non-deterministic behavior.
    """
    def __init__(self, value):
        self.value = value

    def bind(self, function):
        return function(self.value)

    @classmethod
    def unit(cls, value):
        return Identity(value)

    def fmap(self, function):
        return self.__class__(function(self.value))

    def amap(self, function):
        return super(Identity, self).amap(function)


class BasePolicyRule(object):
    pass


def policyM(m):
    class PolicyRule(BasePolicyRule, stateT(m)):
        def __init__(
                self, for_partial, context=None,
                ast=None,
        ):
            if ast is None:
                ast = getattr(for_partial, 'ast', None)

            if context is not None:
                ast = context.with_result(ast)

            self.ast = ast
            super(PolicyRule, self).__init__(for_partial)

        def __repr__(self):
            if self.ast:
                return "<PolicyRule: {}>".format(repr(self.ast))
            return super(PolicyRule, self).__repr__()

        def __deepcopy__(self, memo):
            return copy.copy(self)

        def _bind_policy_rule(self, rule):
            def for_operands(left, right):
                def combined_for_partial(initial_partial):
                    m_results = left.run(initial_partial)
                    def for_m_result(m_result):
                        _, partial = m_result
                        return right.run(partial)
                    return m_results >> for_m_result
                return combined_for_partial

            new_ast = asts.Binding(self.ast, rule.ast)
            return PolicyRule(
                for_operands(self, rule), ast=new_ast
            )

        def bind(self, rule_func):
            if isinstance(rule_func, BasePolicyRule):
                return self._bind_policy_rule(rule_func)

            if not isinstance(rule_func, BasePolicyRuleFunc):
                rule_func = policy_rule_func(m)(rule_func)

            try:
                binding = super(PolicyRule, self).bind(rule_func)
            except:
                logger.debug(
                    "error binding `%r` to rule_func `%r`",
                    self, rule_func
                )
                raise

            new_ast = asts.Binding(self.ast, rule_func.ast)

            return PolicyRule(
                binding.value, ast=new_ast
            )

        def __rshift__(self, function):
            """
            The bind operator. `>>` and `bind` are equivalent.

            Note: this overrides Monad.__rshift__ because the inherited
            implementation makes it impossible to perform the
            `_bind_policy_rule` optimization above.
            """
            result = self.bind(function)
            if not isinstance(result, Monad):
                raise TypeError("Operator '>>' must return a Monad instance.")
            return result

    return PolicyRule


class BasePolicyRuleFunc(object):
    __metaclass__ = ABCMeta


def policy_rule_func(m, rule_func_name=None):
    def decorator(rule_func):
        class PolicyRuleFunc(BasePolicyRuleFunc):
            def __init__(self, rule_func, rule_func_name=None):
                if rule_func_name is None:
                    if hasattr(rule_func, 'ast'):
                        rule_func_name = repr(rule_func.ast)
                    else:
                        rule_func_name = rule_func.__name__
                if rule_func_name == '<lambda>':
                    rule_func_name = (
                        '<lambda {}:>'
                    ).format(
                        ", ".join(inspect.getargspec(rule_func).args) # pylint: disable=deprecated-method
                    )

                if rule_func.__doc__:
                    # this is janky but it works.
                    # if someone goes through the trouble of writing a
                    # docstring for a rule func, it should be accessible
                    # with `help()` and nicely readable.
                    self.__class__.__doc__ = rule_func.__doc__
                    self.__class__.__name__ = (
                        "<PolicyRuleFunc {}>".format(rule_func_name)
                    )

                self.ast = asts.PolicyRuleFunc(rule_func_name)
                self.rule_func = rule_func
                self.rule_func_name = rule_func_name

            def __call__(self, *args, **kwargs):
                for_partial = self.rule_func(*args, **kwargs)
                if isinstance(for_partial, BasePolicyRule):
                    for_partial = for_partial.run

                func_call_ast = asts.PolicyRuleFuncCall(
                    self.ast, args, kwargs
                )
                return policyM(m)(
                    for_partial, context=func_call_ast
                )

            def __repr__(self):
                return "<PolicyRuleFunc {}>".format(self.rule_func_name)

        rule_func = PolicyRuleFunc(rule_func, rule_func_name)
        rule_func.__bases__ = ()
        return rule_func
    return decorator

PolicyRule = BasePolicyRule
PolicyRuleFunc = BasePolicyRuleFunc
