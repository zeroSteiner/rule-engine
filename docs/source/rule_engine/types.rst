:mod:`types`
============

.. module:: rule_engine.types
   :synopsis:

.. versionadded:: 3.2.0

This module contains the internal type definitions and utility functions for working with them.

Functions
---------

.. autofunction:: coerce_value

.. autofunction:: is_integer_number

.. autofunction:: is_natural_number

.. autofunction:: is_numeric

.. autofunction:: is_real_number

.. autofunction:: iterable_member_value_type

Classes
-------

.. autoclass:: DataType
   :members:
   :exclude-members: ARRAY, MAPPING, SET
   :show-inheritance:

   .. automethod:: ARRAY

   .. autoattribute:: BOOLEAN
      :annotation:

   .. autoattribute:: BYTES
      :annotation:

   .. autoattribute:: DATETIME
      :annotation:

   .. autoattribute:: FLOAT
      :annotation:

   .. automethod:: FUNCTION

   .. automethod:: MAPPING

   .. autoattribute:: NULL
      :annotation:

   .. automethod:: SET

   .. autoattribute:: STRING
      :annotation:

   .. autoattribute:: TIMEDELTA
      :annotation:

   .. autoattribute:: UNDEFINED
