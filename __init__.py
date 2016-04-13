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
    set_value, define_as, select, const, path, set_path, with_value,
    check, do, policies, regarding, given, fail, match, attempt,
    permit_values
)
from dramafever.premium.services.policy.partial import Partial
