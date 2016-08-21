"""
Overview and Purpose
====================

Contexts are ordered containers of policy rules, functions that
generate policy rules, and/or sub-contexts. Contexts provide
semantic grouping of policy rules and policy rule generation through
means of deferred value resolution.

The primary goal for Context is to allow the semantic expression of request-
processing policies, so that application-level policy code can be written
with minimal regard for the common underlying non-determinism and
error-propagation behaviors.


General Structure / Scope
-------------------------

Structurally, Context comprises the following parts:
 - An ordered list of items contained in the context
 - A wrapper, within which run the context's contained items
 - Additional semantic annotations such as a context name

A context object may be used for either or both of the following purposes:
 - Contexts may be used to represent a distinct semantic grouping of policy
   rules, as might be expressed by business logic or security requirements.
   This may be granular or broad. This semantic grouping may specify some
   control flow for the contained items, or it may define the way in which
   errors are represented.

   Typically, the semantic meaning of each context is along the lines of
   either: "with regard to some field or parameter", or "with regard to some
   condition being the case".

   Using contexts in this fashion follows the builder pattern - applying
   chained method calls to the context object.

 - Or, the context may represent a value that will exist when policy is run
   on a given request. For instance, `ctx.select("merchant_type")` would
   represent the value for that node.

   A context may be used as this deferred value by passing it as an argument
   to any exposed method on any parent context object.

   Contexts may be used as values in either a context free or a context
   specific manner. The former is more typical, just passing the context to
   some method. Context-specific values can be accessed as a property
   `somectx.value`, and can only be used as arguments for methods in contexts
   descending from the value provider (`somectx`)
"""
from calcifer.contexts.context import (
    Context
)
