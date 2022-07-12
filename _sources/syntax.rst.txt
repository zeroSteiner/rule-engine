.. py:currentmodule:: rule_engine

Rule Syntax
===========
The syntax for creating rules is based off of logical expressions evaluating to either True (matching) or False (non-
matching). Rules support a small set of data types which can be defined as literals or resolved using the Python object
on which the rule is being applied. See the :ref:`Data Types<data-types>` table for a comprehensive list of the
supported types.

Not all supported operations work with all data types as noted in the table below. Rules follow a standard `order of
operations`_.

Grammar
-------
The expression grammar supports a number of operations including basic arithmetic for numerical data and regular
expressions for strings. Operations are type aware and will raise an exception when an incompatible type is used.

.. _data-type-operations:

Supported Operations
^^^^^^^^^^^^^^^^^^^^
The following table outlines all operators that can be used in Rule Engine expressions.

+--------------+------------------------------+-----------------------------------------------------------------+
| Operation    | Description                  | Compatible Data Types                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Arithmetic Operators**                                                                                      |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``+``        | Addition                     | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.STRING`       |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA` |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``-``        | Subtraction                  | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.DATETIME`,    |
|              |                              | :py:attr:`~.DataType.TIMEDELTA`                                 |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``*``        | Multiplication               | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``**``       | Exponent                     | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``/``        | True division                | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``//``       | Floor division               | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``%``        | Modulo                       | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Bitwise-Arithmetic Operators**                                                                              |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``&``        | Bitwise-and :sup:`1`         | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.SET`          |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``|``        | Bitwise-or :sup:`1`          | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.SET`          |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``^``        | Bitwise-xor :sup:`1`         | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.SET`          |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``>>``       | Bitwise right shift :sup:`1` | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``<<``       | Bitwise left shift :sup:`1`  | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Comparison Operators**                                                                                      |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``==``       | Equal to                     | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``!=``       | Not equal to                 | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Arithmetic-Comparison Operators**                                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``>``        | Greater than                 | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BOOLEAN`,     |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA`,|
|              |                              | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.NULL`,        |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
|              |                              | :sup:`2`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``>=``       | Greater than or equal to     | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BOOLEAN`,     |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA`,|
|              |                              | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.NULL`,        |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
|              |                              | :sup:`2`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``<``        | Less than                    | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BOOLEAN`,     |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA`,|
|              |                              | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.NULL`,        |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
|              |                              | :sup:`2`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``<=``       | Less than or equal to        | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BOOLEAN`,     |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA`,|
|              |                              | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.NULL`,        |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
|              |                              | :sup:`2`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Fuzzy-Comparison Operators**                                                                                |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``=~``       | Regex match :sup:`3`         | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``=~~``      | Regex search :sup:`3`        | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``!~``       | Regex match fails :sup:`3`   | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``!~~``      | Regex search fails :sup:`3`  | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Logical Operators**                                                                                         |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``and``      | Logical and                  | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``not``      | Logical not                  | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``or``       | Logical or                   | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``?``, ``:`` | Ternary Operator             | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Accessor Operators**                                                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``.``        | Attribute access             | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.DATETIME`,    |
|              |                              | :py:attr:`~.DataType.TIMEDELTA`, :py:attr:`~.DataType.MAPPING`, |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``&.``       | Safe attribute access        | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.DATETIME`,    |
|              |                              | :py:attr:`~.DataType.TIMEDELTA`, :py:attr:`~.DataType.MAPPING`, |
|              |                              | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``[``        | Item lookup                  | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.MAPPING`,     |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``&[``       | Safe item lookup             | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.MAPPING`,     |
|              |                              | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+

:sup:`1` Bitwise operations support floating point values, but if the value is not a natural number, an
:py:class:`~rule_engine.errors.EvaluationError` will be raised.

:sup:`2` The arithmetic comparison operators support multiple data types however the data type of the left value must be
the same as the data type of the right. For example, a :py:attr:`~.DataType.STRING` can be compared to another
:py:attr:`~.DataType.STRING` but not a :py:attr:`~.DataType.FLOAT`. The technique is the same lexicographical ordering
based sequence comparison `technique used by Python`_.

:sup:`3` When using regular expression operations, the expression on the left is the string to compare and the
expression on the right is the regular expression to use for either the match or search operation.

Accessor Operators
""""""""""""""""""
Some data types support accessor operators to obtain sub-values and attributes. One example is the
:py:attr:`~.DataType.STRING` which supports both attribute and item lookup operations. For example, "length" is a valid
attribute and can be accessed by appending ``.length`` to either a string literal or symbol. Alternatively, a specific
character in a string of characters can be accessed by index. For example, the first character in a string can be
referenced by appending ``[0]`` to either the string literal or symbol. Attempts to lookup either an invalid attribute
or item will raise a :py:class:`~rule_engine.errors.LookupError`.

Both attribute and item lookups have "safe" variants which utilize the ``&`` operator prefix (not to be confused with
the bit-wise and operator which leverages the same symbol). The safe operator version will evaluate to
:py:attr:`~.DataType.NULL` instead of raising an exception when the container value on which the operation is applied is
:py:attr:`~.DataType.NULL`. Additionally, the safe version of item lookup operations will evaluate to
:py:attr:`~.DataType.NULL` instead of raising a :py:class:`~rule_engine.errors.LookupError` exception when the item is
not held within the container. This is analogous the Python's :py:meth:`dict.get` method.

The item lookup operation can also evaluate to an array when a stop boundary is provided. For example to reference the
first four elements of a string by appending ``[0:4]`` to the end of the value. Alternatively, only the ending index
may be specified using ``[:4]``. Finally, just as in Python, negative values can be used to reference the last elements.

Array Comprehension
"""""""""""""""""""
An operation may be able to be applied to each member of an iterable value to generate a new :py:attr:`~.DataType.ARRAY`
composed of the resulting expressions. This could for example be used to determine how many values within an array
match an arbitrary condition. The syntax is very similar to the list comprehension within Python and is composed of
three mandatory components with an optional condition expression. The three required components in order from left to
right are the result expression, the variable assignment and the iterable (followed by the optional condition). Each
component uses a reserved keyword as a delimiter and the entire expression is wrapped within brackets just like an array
literal.

For example, to square an array of numbers: ``[ v ** 2 for v in [1, 2, 3] ]``. In this case, the resulting expression is
the square operation (``v ** 2``) which uses the variable ``v`` defined in the assignment. Finally, the operation is
applied to the array literal ``[1, 2, 3]``, which could have been any iterable value.

An optional condition may be applied to the value before the resulting expression is evaluated using the ``if`` keyword.
Building on the previous example, if only the squares of each odd number was needed, the expression could be updated to:
``[ v ** 2 for v in [1, 2, 3] if v % 2]``. This example uses the modulo operator to filter out even values.

One limitation to the array comprehension syntax when compared to Python's list comprehension is that the variable
assignment may not contain more than one value. There is currently no support for unpacking multiple values like Python
does, (e.g. ``[ v for k,v in my_dict.items() if test(k) ]``.

Ternary Operators
"""""""""""""""""
The ternary operator can be used in place of a traditional "if-then-else" statement. Like other languages the question
mark and colon are used as the expression delimiters. A ternary expression is a combination of a condition followed by
an expression used when the condition is true and ending with an expression used when the condition is false.

For example: ``condition ? true_case : false_case``

Reserved Keywords
^^^^^^^^^^^^^^^^^
The following keywords are reserved and can not be used as the names of symbols.

+-----------+-----------------------------------------------------------------+
| Keyword   | Description                                                     |
+-----------+-----------------------------------------------------------------+
| ``null``  | The :py:class:`NullExpression` literal value                    |
+-----------+-----------------------------------------------------------------+
| **Array Comprehension**                                                     |
+-----------+-----------------------------------------------------------------+
| ``for``   | Array comprehension result and assignment delimiter             |
+-----------+-----------------------------------------------------------------+
| ``if``    | Array comprehension iterable and (optional) condition delimiter |
+-----------+-----------------------------------------------------------------+
| **Booleans** (:py:class:`BooleanExpression` Literals)                       |
+-----------+-----------------------------------------------------------------+
| ``true``  | The "True" boolean value                                        |
+-----------+-----------------------------------------------------------------+
| ``false`` | The "False" boolean value                                       |
+-----------+-----------------------------------------------------------------+
| **Floats** (:py:class:`FloatExpression` Literals)                           |
+-----------+-----------------------------------------------------------------+
| ``inf``   | Floating point value for infinity                               |
+-----------+-----------------------------------------------------------------+
| ``nan``   | Floating point value for not-a-number                           |
+-----------+-----------------------------------------------------------------+
| **Logical Operators**                                                       |
+-----------+-----------------------------------------------------------------+
| ``and``   | Logical "and" operator                                          |
+-----------+-----------------------------------------------------------------+
| ``not``   | Logical "not" operator                                          |
+-----------+-----------------------------------------------------------------+
| ``or``    | Logical "or" operator                                           |
+-----------+-----------------------------------------------------------------+
| **Membership Operators**                                                    |
+-----------+-----------------------------------------------------------------+
| ``in``    | Checks member is in the container                               |
+-----------+-----------------------------------------------------------------+
| **Reserved For Future Use**                                                 |
+-----------+-----------------------------------------------------------------+
| ``elif``  | Reserved for future use                                         |
+-----------+-----------------------------------------------------------------+
| ``else``  | Reserved for future use                                         |
+-----------+-----------------------------------------------------------------+
| ``while`` | Reserved for future use                                         |
+-----------+-----------------------------------------------------------------+

.. _literal-values:

Literal Values
^^^^^^^^^^^^^^
:py:attr:`~.DataType.DATETIME` and :py:attr:`~.DataType.STRING` literal values are specified in a very similar manner by
defining the value as a string of characters enclosed in either single or double quotes. The difference comes in an
optional leading character before the opening quote. Either no leading character or a single ``s`` will specify a
standard :py:attr:`~.DataType.STRING` value, while a single ``d`` will specify a :py:attr:`~.DataType.DATETIME` value.

:py:attr:`~.DataType.DATETIME` literals must be specified in ISO-8601 format. The underlying parsing logic is provided
by :py:meth:`dateutil.parser.isoparse`. :py:attr:`~.DataType.DATETIME` values with no time specified (e.g.
``d"2019-09-23"``) will evaluate to a :py:attr:`~.DataType.DATETIME` of the specified day at exactly midnight.

:py:attr:`~.DataType.TIMEDELTA` literals must be specified in a subset of the ISO-8601 format for durations. Everything
except years and months are supported in `~.DataType.TIMEDELTA` values, to match the underlying representation provided
by the Python standard library.

Example rules showing equivalent literal expressions:

* ``"foobar" == s"foobar"``
* ``d"2019-09-23" == d"2019-09-23 00:00:00"``
* ``t"P1D" == t"PT24H"``

:py:attr:`~.DataType.FLOAT` literals may be expressed in either binary, octal, decimal, or hexadecimal formats. The
binary, octal and hexadecimal formats use the ``0b``, ``0o``, and ``0x`` prefixes respectively. Values in the decimal
format require no prefix and is the default base in which values are represented. Only base-10, decimal values may
include a decimal place component.

Example rules showing equivalent literal expressions:

* ``0b10 == 2``
* ``0o10 == 8``
* ``10.0 == 10``
* ``0x10 == 16``

:py:attr:`~.DataType.FLOAT` literals may also be expressed in scientific notation using the letter ``e``.

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
