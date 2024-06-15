:mod:`ast`
==========

.. module:: rule_engine.ast
   :synopsis:

This module contains the nodes which comprise the abstract syntax tree generated from parsed grammar text.

.. warning::
    The content of this module should be treated as private.

While the code within this module is documented, it is *not* meant to be used by consumers of the package. Directly
accessing and using any object or function within this module should be done with care. Breaking API changes within this
module may not always cause a major version bump. The reason for this is that it is often necessary to update the AST in
an API breaking way in order to add new features.

Classes
-------

.. autoclass:: Assignment
   :members:
   :show-inheritance:
   :special-members: __init__
   :undoc-members:

.. autoclass:: Statement
   :show-inheritance:

Base Classes
~~~~~~~~~~~~

.. autoclass:: ExpressionBase
   :members:
   :exclude-members: result_type
   :show-inheritance:
   :special-members: __init__

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: LeftOperatorRightExpressionBase
   :show-inheritance:

   .. autoattribute:: compatible_types
      :annotation:

   .. automethod:: __init__

.. autoclass:: LiteralExpressionBase
   :show-inheritance:

   .. automethod:: __init__

Left-Operator-Right Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: AddExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: SubtractExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: ArithmeticExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FLOAT

.. autoclass:: ArithmeticComparisonExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: BitwiseExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: BitwiseShiftExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FLOAT

.. autoclass:: ComparisonExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: LogicExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: FuzzyComparisonExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

Literal Expressions
~~~~~~~~~~~~~~~~~~~

.. autoclass:: ArrayExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = ARRAY

.. autoclass:: BooleanExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: BytesExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BYTES

.. autoclass:: DatetimeExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = DATETIME

.. autoclass:: FloatExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FLOAT

.. autoclass:: FunctionExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FUNCTION

.. autoclass:: MappingExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = MAPPING

.. autoclass:: NullExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = NULL

.. autoclass:: SetExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = SET

.. autoclass:: StringExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = STRING

.. autoclass:: TimedeltaExpression
   :show-inheritance:


   .. autoattribute:: result_type
      :annotation: = TIMEDELTA

Miscellaneous Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ComprehensionExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = ARRAY

.. autoclass:: ContainsExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: GetAttributeExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: GetItemExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: GetSliceExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: SymbolExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: TernaryExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: UnaryExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED
