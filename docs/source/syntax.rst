.. py:currentmodule:: rule_engine.ast

Syntax
======
The syntax for creating rules is based off of logical expressions evaluating to
either True (matching) or False (non-matching). Rules support a small set of
data types which can be defined as constants or resolved using the Python object
on which the rule is being applied.

+-------------------------------+-------------------------------+
| Rule Engine Type              | Compatible Python Types       |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.BOOLEAN`  | :py:class:`bool`              |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.DATETIME` | :py:class:`datetime.date`,    |
|                               | :py:class:`datetime.datetime` |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.FLOAT`    | :py:class:`int`,              |
|                               | :py:class:`float`             |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.NULL`     | :py:class:`NoneType`          |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.STRING`   | :py:class:`str`               |
+-------------------------------+-------------------------------+

Not all supported operations work with all data types as noted in the table
below. Rules follow a standard `order of operations`_.

Grammar
-------
The expression grammar supports a number of operations including basic
arithmetic for numerical data and regular expressions for strings. Operations
are type aware and will raise an exception when an incompatible type is used.

Supported Operations
^^^^^^^^^^^^^^^^^^^^

+-----------+------------------------------+--------------------------------+
| Operation | Description                  | Compatible Data Types          |
+-----------+------------------------------+--------------------------------+
| **Arithmetic Operators**                                                  |
+-----------+------------------------------+--------------------------------+
| ``+``     | Addition                     | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``-``     | Subtraction                  | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``*``     | Multiplication               | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``**``    | Exponent                     | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``/``     | True division                | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``//``    | Floor division               | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``%``     | Modulo                       | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| **Bitwise-Arithmetic Operators**                                          |
+-----------+------------------------------+--------------------------------+
| ``&``     | Bitwise-and :sup:`1`         | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``|``     | Bitwise-or :sup:`1`          | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``^``     | Bitwise-xor :sup:`1`         | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``>>``    | Bitwise right shift :sup:`1` | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``<<``    | Bitwise left shift :sup:`1`  | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| **Comparison Operators**                                                  |
+-----------+------------------------------+--------------------------------+
| ``==``    | Equal to                     | *ANY*                          |
+-----------+------------------------------+--------------------------------+
| ``!=``    | Not equal to                 | *ANY*                          |
+-----------+------------------------------+--------------------------------+
| **Arithmetic-Comparison Operators**                                       |
+-----------+------------------------------+--------------------------------+
| ``>``     | Greater than                 | :py:attr:`~DataType.DATETIME`, |
|           |                              | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``>=``    | Greater than or equal to     | :py:attr:`~DataType.DATETIME`, |
|           |                              | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``<``     | Less than                    | :py:attr:`~DataType.DATETIME`, |
|           |                              | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| ``<=``    | Less than or equal to        | :py:attr:`~DataType.DATETIME`, |
|           |                              | :py:attr:`~DataType.FLOAT`     |
+-----------+------------------------------+--------------------------------+
| **Fuzzy-Comparison Operators**                                            |
+-----------+------------------------------+--------------------------------+
| ``=~``    | Regex match :sup:`2`         | :py:attr:`~DataType.NULL`,     |
|           |                              | :py:attr:`~DataType.STRING`    |
+-----------+------------------------------+--------------------------------+
| ``=~~``   | Regex search :sup:`2`        | :py:attr:`~DataType.NULL`,     |
|           |                              | :py:attr:`~DataType.STRING`    |
+-----------+------------------------------+--------------------------------+
| ``!~``    | Regex match fails :sup:`2`   | :py:attr:`~DataType.NULL`,     |
|           |                              | :py:attr:`~DataType.STRING`    |
+-----------+------------------------------+--------------------------------+
| ``!~~``   | Regex search fails :sup:`2`  | :py:attr:`~DataType.NULL`,     |
|           |                              | :py:attr:`~DataType.STRING`    |
+-----------+------------------------------+--------------------------------+
| **Logical Operators**                                                     |
+-----------+------------------------------+--------------------------------+
| ``and``   | Logical and                  | *ANY*                          |
+-----------+------------------------------+--------------------------------+
| ``not``   | Logical not                  | *ANY*                          |
+-----------+------------------------------+--------------------------------+
| ``or``    | Logical or                   | *ANY*                          |
+-----------+------------------------------+--------------------------------+

:sup:`1` Bitwise operations support floating point values, but if the value is
not a natural number, an :py:class:`~rule_engine.errors.EvaluationError` will be
raised.

:sup:`2` When using regular expression operations, the expression on the left is
the string to compare and the expression on the right is the regular expression
to use for either the match or search operation.

Reserved Keywords
^^^^^^^^^^^^^^^^^

+-----------+----------------------------------------------+
| Keyword   | Description                                  |
+-----------+----------------------------------------------+
| ``null``  | The :py:class:`NullExpression` literal value |
+-----------+----------------------------------------------+
| **Booleans** (:py:class:`BooleanExpression` Literals)    |
+-----------+----------------------------------------------+
| ``true``  | The "True" boolean value                     |
+-----------+----------------------------------------------+
| ``false`` | The "False" boolean value                    |
+-----------+----------------------------------------------+
| **Floats** (:py:class:`FloatExpression` Literals)        |
+-----------+----------------------------------------------+
| ``inf``   | Floating point value for infinity            |
+-----------+----------------------------------------------+
| ``nan``   | Floating point value for not-a-number        |
+-----------+----------------------------------------------+
| **Logical Operators**                                    |
+-----------+----------------------------------------------+
| ``and``   | Logical "and" operator                       |
+-----------+----------------------------------------------+
| ``not``   | Logical "not" operator                       |
+-----------+----------------------------------------------+
| ``or``    | Logical "or" operator                        |
+-----------+----------------------------------------------+

.. _Order of operations: https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
