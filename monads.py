"""
`dramafever.premium.services.policy.monads` module

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
from pymonad import Monad


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
                    m_new_result = function(value)(state)

                    return m_new_result

                return self(state) >> for_state_result
            return newState

        def __call__(self, state):
            return self.value(state)

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
        return super(Identity, self).fmap(function)

    def amap(self, function):
        return super(Identity, self).amap(function)
