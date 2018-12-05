Syntax
======
The syntax for creating rules is based off of logical expressions evaluating to
either True (matching) or False (non-matching). Rules support a small set of
data types which can be defined as constants or resolved using the Python object
on which the rule is being applied.

* :py:attr:`~rule_engine.ast.DataType.BOOLEAN`
* :py:attr:`~rule_engine.ast.DataType.FLOAT`
* :py:attr:`~rule_engine.ast.DataType.STRING`

Not all supported operations work with all data types as noted in the table
below. Rules follow a standard `order of operations`_.

Grammar
-------
The expression grammar supports a number of operations including basic
arithmetic for numerical data and regular expressions for strings. Operations
are type aware and will raise an exception when an incompatible type is used.

Supported Operations
^^^^^^^^^^^^^^^^^^^^

+-----------+------------------------------+---------------------------------------------+
| Operation | Description                  | Compatible Data Types                       |
+-----------+------------------------------+---------------------------------------------+
| ``+``     | Addition                     | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``-``     | Subtraction                  | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``*``     | Multiplication               | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``**``    | Exponent                     | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``/``     | True division                | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``//``    | Floor division               | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``%``     | Modulo                       | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``&``     | Bitwise-and :sup:`1`         | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``|``     | Bitwise-or :sup:`1`          | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``^``     | Bitwise-xor :sup:`1`         | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``>>``    | Bitwise right shift :sup:`1` | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``<<``    | Bitwise left shift :sup:`1`  | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``>``     | Greater than                 | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``>=``    | Greater than or equal to     | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``<``     | Less than                    | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``<=``    | Less than or equal to        | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+------------------------------+---------------------------------------------+
| ``==``    | Equal to                     | *ANY*                                       |
+-----------+------------------------------+---------------------------------------------+
| ``!=``    | Not equal to                 | *ANY*                                       |
+-----------+------------------------------+---------------------------------------------+
| ``=~``    | Regex match :sup:`2`         | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+------------------------------+---------------------------------------------+
| ``=~~``   | Regex search :sup:`2`        | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+------------------------------+---------------------------------------------+
| ``!~``    | Regex match fails :sup:`2`   | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+------------------------------+---------------------------------------------+
| ``!~~``   | Regex search fails :sup:`2`  | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+------------------------------+---------------------------------------------+
| ``and``   | Logical and                  | *ANY*                                       |
+-----------+------------------------------+---------------------------------------------+
| ``or``    | Logical or                   | *ANY*                                       |
+-----------+------------------------------+---------------------------------------------+

:sup:`1` Bitwise operations support floating point values, but if the value is
not a natural number a :py:class:`~rule_engine.errors.EvaluationError` will be
raised.

:sup:`2` When using regular expression operations, the expression on the left is
the string to compare and the expression on the right is the regular expression
to use for either the match or search operation.

Reserved Keywords
^^^^^^^^^^^^^^^^^

+-----------+---------------------------------------+
| Keyword   | Description                           |
+-----------+---------------------------------------+
| Booleans                                          |
+-----------+---------------------------------------+
| ``true``  | The "True" boolean value              |
+-----------+---------------------------------------+
| ``false`` | The "False" boolean value             |
+-----------+---------------------------------------+
| Floats                                            |
+-----------+---------------------------------------+
| ``inf``   | Floating point value for infinity     |
+-----------+---------------------------------------+
| ``nan``   | Floating point value for not-a-number |
+-----------+---------------------------------------+
| Logical Operators                                 |
+-----------+---------------------------------------+
| ``and``   | Logical "and" operator                |
+-----------+---------------------------------------+
| ``not``   | Logical "not" operator                |
+-----------+---------------------------------------+
| ``or``    | Logical "or" operator                 |
+-----------+---------------------------------------+

.. _Order of operations: https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
