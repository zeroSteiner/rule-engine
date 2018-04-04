:mod:`ast`
==========

.. module:: rule_engine.ast
   :synopsis:

This module contains the nodes which comprise the abstract syntax tree generated
from parsed grammar text.

Functions
---------

.. autofunction:: rule_engine.ast.is_natural_number

.. autofunction:: rule_engine.ast.is_real_number

Classes
-------

.. autoclass:: rule_engine.ast.DataType
   :members:
   :show-inheritance:

   .. autoattribute:: BOOLEAN
      :annotation:

   .. autoattribute:: FLOAT
      :annotation:

   .. autoattribute:: STRING
      :annotation:

.. autoclass:: rule_engine.ast.Statement
   :show-inheritance:

Base Classes
~~~~~~~~~~~~

.. autoclass:: rule_engine.ast.ExpressionBase
   :members:
   :show-inheritance:
   :special-members: __init__

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: rule_engine.ast.LeftOperatorRightExpressionBase
   :show-inheritance:

   .. autoattribute:: compatible_types
      :annotation:

   .. automethod:: __init__

.. autoclass:: rule_engine.ast.LiteralExpressionBase
   :show-inheritance:

   .. automethod:: __init__

Left-Operator-Right Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: rule_engine.ast.ArithmeticExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FLOAT

.. autoclass:: rule_engine.ast.BitwiseExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FLOAT

.. autoclass:: rule_engine.ast.ComparisonExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: rule_engine.ast.LogicExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

Literal Expressions
~~~~~~~~~~~~~~~~~~~

.. autoclass:: rule_engine.ast.BooleanExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = BOOLEAN

.. autoclass:: rule_engine.ast.FloatExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = FLOAT

.. autoclass:: rule_engine.ast.StringExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = STRING

Miscellaneous Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: rule_engine.ast.SymbolExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: rule_engine.ast.TernaryExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED

.. autoclass:: rule_engine.ast.UnaryExpression
   :show-inheritance:

   .. autoattribute:: result_type
      :annotation: = UNDEFINED
