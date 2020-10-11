.. py:currentmodule:: rule_engine.ast

Rule Syntax
===========
The syntax for creating rules is based off of logical expressions evaluating to either True (matching) or False (non-
matching). Rules support a small set of data types which can be defined as constants or resolved using the Python object
on which the rule is being applied.

+-------------------------------+-------------------------------+
| Rule Engine Data Type         | Compatible Python Types       |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.ARRAY`    | :py:class:`list`,             |
|                               | :py:class:`tuple`             |
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

Not all supported operations work with all data types as noted in the table below. Rules follow a standard `order of
operations`_.

Grammar
-------
The expression grammar supports a number of operations including basic arithmetic for numerical data and regular
expressions for strings. Operations are type aware and will raise an exception when an incompatible type is used.

Supported Operations
^^^^^^^^^^^^^^^^^^^^
The following table outlines all operators that can be used in Rule Engine expressions.

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
| ``>``     | Greater than                 | *ANY* :sup:`2`                 |
+-----------+------------------------------+--------------------------------+
| ``>=``    | Greater than or equal to     | *ANY* :sup:`2`                 |
+-----------+------------------------------+--------------------------------+
| ``<``     | Less than                    | *ANY* :sup:`2`                 |
+-----------+------------------------------+--------------------------------+
| ``<=``    | Less than or equal to        | *ANY* :sup:`2`                 |
+-----------+------------------------------+--------------------------------+
| **Fuzzy-Comparison Operators**                                            |
+-----------+------------------------------+--------------------------------+
| ``=~``    | Regex match :sup:`3`         | :py:attr:`~DataType.NULL`,     |
|           |                              | :py:attr:`~DataType.STRING`    |
+-----------+------------------------------+--------------------------------+
| ``=~~``   | Regex search :sup:`3`        | :py:attr:`~DataType.NULL`,     |
|           |                              | :py:attr:`~DataType.STRING`    |
+-----------+------------------------------+--------------------------------+
| ``!~``    | Regex match fails :sup:`3`   | :py:attr:`~DataType.NULL`,     |
|           |                              | :py:attr:`~DataType.STRING`    |
+-----------+------------------------------+--------------------------------+
| ``!~~``   | Regex search fails :sup:`3`  | :py:attr:`~DataType.NULL`,     |
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

:sup:`1` Bitwise operations support floating point values, but if the value is not a natural number, an
:py:class:`~rule_engine.errors.EvaluationError` will be raised.

:sup:`2` The arithmetic comparison operators support multiple data types however the data type of the left value must be
the same as the data type of the right. For example, a :py:attr:`~DataType.STRING` can be compared to another
:py:attr:`~DataType.STRING` but not a :py:attr:`~DataType.FLOAT`. The technique is the same lexicographical ordering
based sequence comparison `technique used by Python`_.

:sup:`3` When using regular expression operations, the expression on the left is the string to compare and the
expression on the right is the regular expression to use for either the match or search operation.

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
| **Membership Operators**                                 |
+-----------+----------------------------------------------+
| ``in``    | Checks member is in the container            |
+-----------+----------------------------------------------+

.. _literal-values:

Literal Values
^^^^^^^^^^^^^^
:py:attr:`~DataType.DATETIME` and :py:attr:`~DataType.STRING` literal values are specified in a very similar manner by
defining the value as a string of characters enclosed in either single or double quotes. The difference comes in an
optional leading character before the opening quote. Either no leading character or a single ``s`` will specify a
standard :py:attr:`~DataType.STRING` value, while a single ``d`` will specify a :py:attr:`~DataType.DATETIME` value.

:py:attr:`~DataType.DATETIME` literals must be specified in ISO-8601 format. The underlying parsing logic is provided by
:py:meth:`dateutil.parser.isoparse`. :py:attr:`~DataType.DATETIME` values with no time specified (e.g.
``d"2019-09-23"``) will evaluate to a :py:attr:`~DataType.DATETIME` of the specified day at exactly midnight.

Example rules showing equivalent literal expressions:

* ``"foobar" == s"foobar"``
* ``d"2019-09-23" == d"2019-09-23 00:00:00"``

:py:attr:`~DataType.FLOAT` literals may be expressed in either binary, octal, decimal, or hexadecimal formats. The
binary, octal and hexadecimal formats use the ``0b``, ``0o``, and ``0x`` prefixes respectively. Values in the decimal
format require no prefix and is the default base in which values are represented. Only base-10, decimal values may
include a decimal place component.

Example rules showing equivalent literal expressions:

* ``0b10 == 2``
* ``0o10 == 8``
* ``10.0 == 10``
* ``0x10 == 16``

:py:attr:`~DataType.FLOAT` literals may also be expressed in scientific notation using the letter ``e``.

Example rules show equivalent literal expressions:

* ``1E0 == 1``
* ``1e0 == 1``
* ``1.0e0 == 1``

.. py:currentmodule:: rule_engine

.. _builtin-symbols:

Builtin Symbols
---------------
The following symbols are provided by default using the :py:meth:`~engine.Builtins.from_defaults` method. These symbols
can be accessed through the ``$`` prefix, e.g. ``$pi``. The default values can be overridden by defining a custom
subclass of :py:class:`~engine.Context` and setting the :py:attr:`~engine.Context.builtins` attribute.

Math Related
^^^^^^^^^^^^

* ``e`` (type: :py:attr:`~ast.DataType.FLOAT`) -- The mathematical constant *e* (2.71828...).
* ``pi`` (type: :py:attr:`~ast.DataType.FLOAT`) -- The mathematical constant *pi* (3.14159...).

Regular Expression Related
^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``re_groups`` (type: :py:attr:`~ast.DataType.ARRAY`) -- An array of strings from the last regular expression match as
  defined by the regular expression itself. See documentation on `grouping`_ for more information. If no match has taken
  place, this value is :py:attr:`~ast.DataType.NULL`.

  .. note:: For technical reasons, this symbol is provided by the default :py:attr:`~engine.Context` and is not included
    within the :py:meth:`~engine.Builtins.from_defaults`. This means that unlike the other symbols listed here, it will
    be unavailable if the default builtins are replaced.

Timestamp Related
^^^^^^^^^^^^^^^^^

* ``now`` (type: :py:attr:`~ast.DataType.DATETIME`) -- The current timestamp (including time) using the default timezone
  from :py:attr:`~engine.Context.default_timezone`.
* ``today`` (type: :py:attr:`~ast.DataType.DATETIME`) -- The current timestamp, (excluding time, normalized to midnight
  00:00:00) using the default timezone from :py:attr:`~engine.Context.default_timezone`.

.. _grouping: https://docs.python.org/3/howto/regex.html#grouping
.. _Order of operations: https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
.. _technique used by Python: https://docs.python.org/3/tutorial/datastructures.html#comparing-sequences-and-other-types