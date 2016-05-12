"""
`dramafever.premium.services.policy` module

The purpose of this module is to provide runtime validation and template
generation for commands.

This module provides low-level operators to describe the non-deterministic
manipulation of a "Policy Partial" data structure to be used in validation and
template generation. The operators are designed to provide flexible
tooling for the creation of high-level policy rules.
"""
from dramafever.premium.services.policy.contexts import Context
from dramafever.premium.services.policy.operators import (
    attempt,
    append_value,
    check,
    children,
    collect,
    define_as,
    each,
    fail,
    forbid_value,
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
    require_value,
    scope,
    select,
    set_path,
    set_value,
    trace,
    unit,
    unit_value,
    unless_errors,
    with_value,
    wrap_context,
)
from dramafever.premium.services.policy.partial import Partial
from dramafever.premium.services.policy.monads import (
    PolicyRule, PolicyRuleFunc
)
from dramafever.premium.services.policy.policy import BasePolicy
