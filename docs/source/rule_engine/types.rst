:mod:`types`
============

.. module:: rule_engine.types
   :synopsis:

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

   .. autoattribute:: ARRAY
      :annotation:

   .. autoattribute:: BOOLEAN
      :annotation:

   .. autoattribute:: DATETIME
      :annotation:

   .. autoattribute:: FLOAT
      :annotation:

   .. autoattribute:: MAPPING
      :annotation:

   .. autoattribute:: NULL
      :annotation:

   .. autoattribute:: SET
      :annotation:

   .. autoattribute:: STRING
      :annotation:
