# -*- coding: utf-8 -*-
"""
calcifer top-level module

The purpose of this module is to provide runtime validation and template
generation for commands.

This module provides low-level operators to describe the non-deterministic
manipulation of a "Policy Partial" data structure to be used in validation and
template generation. The operators are designed to provide flexible
tooling for the creation of high-level policy rules.
"""
from calcifer.contexts import Context
from calcifer.operators import (
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
    match,
    permit_values,
    policies,
    pop_context,
    push_context,
    regarding,
    require_value,
    scope,
    select,
    set_value,
    trace,
    unit,
    unit_value,
    unless_errors,
    wrap_context,
)
from calcifer.partial import Partial
from calcifer.monads import (
    PolicyRule, PolicyRuleFunc
)
from calcifer.policy import BasePolicy


version_info = (0, 0, 0)
__version__ = '.'.join(str(v) for v in version_info[:3])
