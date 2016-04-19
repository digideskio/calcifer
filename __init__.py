"""
`dramafever.premium.services.policy` module

The purpose of this module is to provide runtime validation and template
generation for commands.

This module provides low-level operators to describe the non-deterministic
manipulation of a "Policy Partial" data structure to be used in validation and
template generation. The operators are designed to provide flexible
tooling for the creation of high-level policy rules.
"""
from dramafever.premium.services.policy.operators import (
    attempt,
    check,
    define_as,
    fail,
    get_node,
    get_value,
    given,
    match,
    path,
    permit_values,
    policies,
    pop_context,
    push_context,
    regarding,
    scope,
    select,
    set_path,
    set_value,
    unit,
    unit_value,
    with_value,
    wrap_context,
)
from dramafever.premium.services.policy.partial import Partial
from dramafever.premium.services.policy.monads import (
    PolicyRule, PolicyRuleFunc
)
