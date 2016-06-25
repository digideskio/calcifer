API
---

.. automodule:: calcifer
   :members:

.. automodule:: calcifer.operators

   Partial Operators
   =================

   .. autofunction:: scope
   .. autofunction:: select
   .. autofunction:: get_node
   .. autofunction:: define_as
   .. autofunction:: get_value
   .. autofunction:: set_value
   .. autofunction:: append_value
   .. autofunction:: children


   Control-flow Operators
   ======================

   .. autofunction:: unit
   .. autofunction:: unit_value
   .. autofunction:: collect
   .. autofunction:: policies
   .. autofunction:: regarding
   .. autofunction:: check
   .. autofunction:: each


   Non-Determinism
   ===============

   .. autofunction:: match
   .. autofunction:: require_value
   .. autofunction:: forbid_value
   .. autofunction:: permit_values
   .. autofunction:: fail


   Error-Handling
   ==============

   .. autofunction:: attempt
   .. autofunction:: trace
   .. autofunction:: unless_errors


   Context Annotation
   ==================

   .. autofunction:: push_context
   .. autofunction:: pop_context
   .. autofunction:: wrap_context
