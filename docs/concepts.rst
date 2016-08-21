Concepts
========

Overview
--------

Calcifer aims to provide a computing model for describing data processing
procedures that closely match policies in a source domain.

Ultimately, Calcifer seeks to provide a means to build systems that not only
validate input, but also "fill in the gaps" for incomplete or incorrect input.
Calcifer offers systems the ability to generate template descriptions of valid
input, as well as automatically indicate, with source domain semantics, what
makes a given input invalid.

Calcifer hopes to offer this functionality with minimal impedance, to the end
that code using the library can still resemble traditional imperative and/or
functional paradigms.


Policy
------

The term **policy** is used to refer specifically to Calcifer *"policies"*, or
computations in the Calcifer model. Policies are designed to allow analogous
description of various kinds of real-world policies, e.g. software business
logic, request validation, and data pipeline operation.

Policy computation is stateful and matches imperative programming styles in
that values are mutable and statements are ordered. It is often more natural
to describe procedures from a source domain in a non-pure [#]_, state-driven
fashion.

An example policy expression:

.. code-block:: python

   from calcifer import Policy

   @Policy
   def allowed_favorites_policy(ctx):
       # sorry green
       ctx.select("favorite_color").whitelist_values(["purple", "orange"])

This specifies that ``"purple"`` and ``"orange"`` are the only two valid choices
for ``favorite_color``.

Usage is as follows:

.. code-block:: python

    >>> allowed_favorites_policy.run({"favorite_color": "purple"})
    [{'favorite_color': 'purple'}]

    >>> allowed_favorites_policy.run({"favorite_color": "red"}) # not valid
    [{'favorite_color': 'red',
      'errors': [{u'code': 'INVALID_VALUE_SELECTION',
        u'context': [<policy 'allowed_favorites_policy'>,
         <policy 'select("favorite_color")'>,
         <policy 'whitelist_values'>],
        u'scope': u'/favorite_color',
        u'value': 'red',
        u'values': ['purple', 'orange']}]}]

    >>> allowed_favorites_policy.run({}) # anything goes!
    [{'favorite_color': 'purple'}, {'favorite_color': 'orange'}]





.. [#] Future versions of Calcifer may attempt to model state less implicitly
   in order to encourage safer programming.


Computing Model
---------------

Calcifer employs the following concepts to create its computing model:

Higher-Order Trees
    The data maintained in the computation of policies is structured as a
    tree where each node may have a value, and/or have a template description
    of values, or have neither of these.

    Templates afford the ability to describe constraints on acceptable values
    without requiring producing actual instances of values.

    Nodes can have neither a value or a template and be completely unknown,
    the system attempts to make assumptions as nodes get referenced through
    usage. This allows defining a node very precisely several levels deep,
    without committing to defining all the parent nodes upfront.

Scoping and Policy Partials
    In addition to the underlying tree, which can be thought of merely as
    a reference to its own root, the computation model also maintains a
    pointer to a given sub-tree or node. This is similar to jsonpointer or
    CSS selectors.

    This allows modular computations - individual sub-policies can be defined
    that operate on a scoped subset of the rest of the data.

    At any given step in a particular computation, the whole of the computing
    model's "data memory" is known as a **partial**. Partials are isomorphic
    to tuples of the form :math:`(tree, scope)`,

Free Computation, First-class Context-awareness
    Calcifer operates in a free [#]_ fashion, meaning that policies are built
    as first-class values: operations for a given policy are specified and
    defined as data.

    At a high level, **contexts** define nested collections of operating
    conditions for individual computations. The particular context at any
    step in a policy computation is analagous to the usual point-in-time
    instruction-pointer stack.

    The difference is - the "code as data" structure gives certain affordances.

    Namely, contexts themselves are first-class and can be passed around as
    values, providing certain "convenient" capabilities, such as customized
    error handling and the composition/nesting of contexts as "regular" Python
    variables. Calcifer Context objects are individually strange little Turing
    toys, able to behave in different ways, depending how they are put together.

Non-Determinism
    Mimicking the common *logic programming* paradigm, Calcifer's computing
    model allows for the forking and pruning of operations. Policy
    determination may return 0 results, 1 result exactly, or any number of
    valid results.

    The over-arching mechanism is akin to the parallel computation of different
    policy alternatives, removing failing policies along the way, and producing
    some list of results.

.. [#] The concept is that of a *Free Monad*, giving access to the
   underlying AST of the computation at definition runtime as well as
   execution runtime.


Usage Examples of Features
--------------------------

.. role:: python(code)
   :language: python

Deferred Values - Rudimentary Role Permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Given some data access for permission lookup based on role:

.. code-block:: python

   def fetch_allowed_permissions(role='nobody'):
       """
       Given some system role, return allowed permissions
       """
       # ...
       # connect to db, fetch from an API, load from settings, whatever.
       # ...
       return list(permissions)

The policy for an incoming request can be expressed as follows, where
``"role"`` and ``"permission"`` are properties of the incoming request.

.. code-block:: python

   from calcifer import Policy

   @Policy
   def allowed_permissions_policy(ctx):
       role_ctx = ctx.select("role") # available when the policy is computed
       fetched_permissions_ctx = ctx.apply(
           fetch_permitted_values, # apply this function
           role_ctx # over this value
       )

       ctx.select("permission").whitelist_values(
           fetched_permissions_ctx
       )

The :python:`_ctx` suffix is used to indicate that the variables do not hold actual
values. :python:`role_ctx` can be verbalized as "the context where the value of the
role is known", or :python:`fetched_permissions_ctx` can similarly be thought of as
"the context where the permissions have been fetched."

(Sometimes these contexts are never reached, a topic for another section,
but N.B. that these are first-class values and subject to control flow)

In this example, Context values are used in three capacities:

1. As deferreds: :python:`role_ctx` is used as a stand-in for the value of the role,
   whenever, say, a request comes in, and the system is calculating what
   actions to allow.

2. As function applications over deferred values: :python:`ctx.apply()` takes args
   :python:`function_or_function_ctx, *values_or_value_ctxes`, and connects the
   plumbing to ensure that the function is called correctly when values are
   available.

3. As stateful operators: :python:`ctx.select("permission").whitelist_values(...)`
   indicates that the policy computation may have more than one valid result.
   This is the forking operation described above: once the policy knows
   the fetched permissions, the policy specifies some number of valid
   alternatives.





