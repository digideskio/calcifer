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
    catch_attempt,
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
    pop_value,
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
    PolicyRule, PolicyRuleFunc, policy_rule, policy_rule_func,
)
from calcifer.policy import BasePolicy
from calcifer.policy import DefaultPolicy as Policy

from calcifer._version import __version__
