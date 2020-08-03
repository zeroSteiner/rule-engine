:mod:`ast`
==========

.. module:: rule_engine.ast
   :synopsis:

This module contains the nodes which comprise the abstract syntax tree generated
from parsed grammar text.

Functions
---------

.. autofunction:: coerce_value

.. autofunction:: is_integer_number

.. autofunction:: is_natural_number

.. autofunction:: is_numeric

.. autofunction:: is_real_number

Classes
-------

.. autoclass:: DataType
   :members:
   :exclude-members: ARRAY
   :show-inheritance:

   .. autoattribute:: ARRAY
      :annotation:

   .. autoattribute:: BOOLEAN
      :annotation:

   .. autoattribute:: DATETIME
      :annotation:

   .. autoattribute:: FLOAT
      :annotation:

   .. autoattribute:: NULL
      :annotation:

   .. autoattribute:: STRING
      :annotation:

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

.. autoclass:: BooleanExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: FloatExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FLOAT

.. autoclass:: NullExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = NULL

.. autoclass:: StringExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = STRING

Miscellaneous Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ContainsExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: GetAttributeExpression
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
