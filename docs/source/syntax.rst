.. py:currentmodule:: rule_engine.ast

Syntax
======
The syntax for creating rules is based off of logical expressions evaluating to
either True (matching) or False (non-matching). Rules support a small set of
data types which can be defined as constants or resolved using the Python object
on which the rule is being applied.

+-------------------------------+-------------------------------+
| Rule Engine Data Type         | Compatible Python Types       |
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
The following keywords are reserved and can not be used as the names of symbols.

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

Literal Values
^^^^^^^^^^^^^^
STRING and DATETIME literal values are specified in a very similar manner by
defining the value as a string of characters enclosed in either single or double
quotes. The difference comes in an optional leading character before the opening
quote. Either no leading character or a single ``s`` will specify a standard
STRING value, while a single ``d`` will specify a DATETIME value.

DATETIME literals must be specified in ISO-8601 format. The underlying parsing
logic is provided by :py:meth:`dateutil.parser.isoparse`. DATETIME values with
no time specified (e.g. ``d"2019-09-23"``) will evaluate to a DATETIME of the
specified day at exactly midnight.

Example rules showing equivalent literal expressions:

* ``"foobar" == s"foobar"``
* ``d"2019-09-23" == d"2019-09-23 00:00:00"``


.. _Order of operations: https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
