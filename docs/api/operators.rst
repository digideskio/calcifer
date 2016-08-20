Low-level Policy Operators
--------------------------

.. automodule:: calcifer.operators
   :noindex:

   Partial Operators
   =================

   .. autofunction:: scope()
   .. autofunction:: select(scope, set_path=False)
   .. autofunction:: get_node()
   .. autofunction:: define_as(node)
   .. autofunction:: get_value()
   .. autofunction:: set_value(value)
   .. autofunction:: append_value(value)
   .. autofunction:: children()


   Control-flow Operators
   ======================

   .. autofunction:: unit(value)
   .. autofunction:: unit_value(node)
   .. autofunction:: collect(*rule_funcs)
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
