Grammar
=======
The expression grammar supports a number of operations including basic
arithmetic for numerical data and regular expressions for strings. Operations
are type aware and will raise an exception when an incompatible type is used.

Supported Operations
--------------------

+-----------+-----------------------------+---------------------------------------------+
| Operation | Description                 | Compatible Data Types                       |
+-----------+-----------------------------+---------------------------------------------+
| ``+``     | Addition                    | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``-``     | Subtraction                 | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``*``     | Multiplication              | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``**``    | Exponent                    | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``/``     | True division               | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``//``    | Floor division              | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``%``     | Modulo                      | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``&``     | Bitwise-and                 | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``|``     | Bitwise-or                  | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``^``     | Bitwise-xor                 | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``>>``    | Bitwise right shift         | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``<<``    | Bitwise left shift          | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``>``     | Greater than                | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``>=``    | Greater than or equal to    | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``<``     | Less than                   | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``<=``    | Less than or equal to       | :py:attr:`~rule_engine.ast.DataType.FLOAT`  |
+-----------+-----------------------------+---------------------------------------------+
| ``==``    | Equal to                    | *ANY*                                       |
+-----------+-----------------------------+---------------------------------------------+
| ``!=``    | Not equal to                | *ANY*                                       |
+-----------+-----------------------------+---------------------------------------------+
| ``=~``    | Regex match :sup:`1`        | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+-----------------------------+---------------------------------------------+
| ``=~~``   | Regex search :sup:`1`       | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+-----------------------------+---------------------------------------------+
| ``!~``    | Regex match fails :sup:`1`  | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+-----------------------------+---------------------------------------------+
| ``!~~``   | Regex search fails :sup:`1` | :py:attr:`~rule_engine.ast.DataType.STRING` |
+-----------+-----------------------------+---------------------------------------------+
| ``and``   | Logical and                 | *ANY*                                       |
+-----------+-----------------------------+---------------------------------------------+
| ``or``    | Logical or                  | *ANY*                                       |
+-----------+-----------------------------+---------------------------------------------+

:sup:`1` When using regular expression operations, the expression on the left is
the string to compare and the expression on the right is the regular expression
to use for either the match or search operation.
