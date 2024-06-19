:mod:`errors`
=============

.. module:: rule_engine.errors
   :synopsis:

This module contains the exceptions raised by the package.

Data
----

.. autodata:: UNDEFINED

Exceptions
----------

.. autoexception:: AttributeResolutionError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: AttributeTypeError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: BytesSyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: DatetimeSyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: FloatSyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: EngineError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: EvaluationError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: FunctionCallError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: LookupError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: RegexSyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: RuleSyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: StringSyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: SymbolResolutionError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: SymbolTypeError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: SyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoexception:: TimedeltaSyntaxError
   :members:
   :show-inheritance:
   :special-members: __init__

Exception Hierarchy
-------------------

The class hierarchy for Rule Engine exceptions is:

.. code-block:: text

   EngineError
    +-- EvaluationError
         +-- AttributeResolutionError
         +-- AttributeTypeError
         +-- FunctionCallError
         +-- LookupError
         +-- SymbolResolutionError
         +-- SymbolTypeError
    +-- SyntaxError
         +-- BytesSyntaxError
         +-- DatetimeSyntaxError
         +-- FloatSyntaxError
         +-- RegexSyntaxError
         +-- RuleSyntaxError
         +-- StringSyntaxError
         +-- TimedeltaSyntaxError
