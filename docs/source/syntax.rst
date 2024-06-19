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
| ``+``        | Addition                     | :py:attr:`~.DataType.BYTES`, :py:attr:`~.DataType.DATETIME`,    |
|              |                              | :py:attr:`~.DataType.FLOAT`, py:attr:`~.DataType.STRING`,       |
|              |                              | :py:attr:`~.DataType.TIMEDELTA` :sup:`1`                        |
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
| ``&``        | Bitwise-and :sup:`2`         | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.SET`          |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``|``        | Bitwise-or :sup:`2`          | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.SET`          |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``^``        | Bitwise-xor :sup:`2`         | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.SET`          |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``>>``       | Bitwise right shift :sup:`2` | :py:attr:`~.DataType.FLOAT`                                     |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``<<``       | Bitwise left shift :sup:`2`  | :py:attr:`~.DataType.FLOAT`                                     |
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
|              |                              | :sup:`3`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``>=``       | Greater than or equal to     | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BOOLEAN`,     |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA`,|
|              |                              | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.NULL`,        |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
|              |                              | :sup:`3`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``<``        | Less than                    | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BOOLEAN`,     |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA`,|
|              |                              | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.NULL`,        |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
|              |                              | :sup:`3`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``<=``       | Less than or equal to        | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BOOLEAN`,     |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.TIMEDELTA`,|
|              |                              | :py:attr:`~.DataType.FLOAT`, :py:attr:`~.DataType.NULL`,        |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
|              |                              | :sup:`3`                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Fuzzy-Comparison Operators**                                                                                |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``=~``       | Regex match :sup:`4`         | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``=~~``      | Regex search :sup:`4`        | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``!~``       | Regex match fails :sup:`4`   | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``!~~``      | Regex search fails :sup:`4`  | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.STRING`        |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Logical Operators**                                                                                         |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``and``      | Logical and                  | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``not``      | Logical not                  | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``or``       | Logical or                   | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``?``, ``:`` | Ternary operator             | *ANY*                                                           |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Membership Operators**                                                                                      |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``in``       | Membership check             | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BYTES`,       |
|              |                              | :py:attr:`~.DataType.MAPPING`, :py:attr:`~.DataType.SET`,       |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
+--------------+------------------------------+-----------------------------------------------------------------+
| **Accessor Operators**                                                                                        |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``.``        | Attribute access             | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BYTES`,       |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.MAPPING`,  |
|              |                              | :py:attr:`~.DataType.SET`, :py:attr:`~.DataType.STRING`,        |
|              |                              | :py:attr:`~.DataType.TIMEDELTA`                                 |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``&.``       | Safe attribute access        | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BYTES`,       |
|              |                              | :py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.MAPPING`,  |
|              |                              | :py:attr:`~.DataType.NULL`, :py:attr:`~.DataType.SET`,          |
|              |                              | :py:attr:`~.DataType.STRING`, :py:attr:`~.DataType.TIMEDELTA`   |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``[``        | Item lookup                  | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BYTES`,       |
|              |                              | :py:attr:`~.DataType.MAPPING`, :py:attr:`~.DataType.STRING`     |
+--------------+------------------------------+-----------------------------------------------------------------+
| ``&[``       | Safe item lookup             | :py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.BYTES`,       |
|              |                              | :py:attr:`~.DataType.MAPPING`, :py:attr:`~.DataType.NULL`,      |
|              |                              | :py:attr:`~.DataType.STRING`                                    |
+--------------+------------------------------+-----------------------------------------------------------------+

:sup:`1` Addition operations involving :py:attr:`~.DataType.DATETIME` and :py:attr:`~.DataType.TIMEDELTA` must have a
:py:attr:`~.DataType.TIMEDELTA` value on the right. :py:attr:`~.DataType.TIMEDELTA` values can be added to other
:py:attr:`~.DataType.TIMEDELTA` values, or :py:attr:`~.DataType.DATETIME` values but :py:attr:`~.DataType.DATETIME` can
not be added to other :py:attr:`~.DataType.DATETIME` values. The remaining types (:py:attr:`~.DataType.BYTES`,
:py:attr:`~.DataType.STRING`, and :py:attr:`~.DataType.FLOAT`) must be added to values of the same type.

:sup:`2` Bitwise operations support floating point values, but if the value is not a natural number, an
:py:class:`~rule_engine.errors.EvaluationError` will be raised.

:sup:`3` The arithmetic comparison operators support multiple data types however the data type of the left value must be
the same as the data type of the right. For example, a :py:attr:`~.DataType.STRING` can be compared to another
:py:attr:`~.DataType.STRING` but not a :py:attr:`~.DataType.FLOAT`. The technique is the same lexicographical ordering
based sequence comparison `technique used by Python`_.

:sup:`4` When using regular expression operations, the expression on the left is the string to compare and the
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

Function Calls
^^^^^^^^^^^^^^

Function calls can be preformed on function symbols by placing parenthesis after them. The parenthesis contain zero or
more argument expressions to pass to the function. Functions support optional positional arguments. For example, a
function can take two arguments and one or both can specify a default value and then be omitted when called. Functions
do not support keyword arguments.

Using the :ref:`builtin split<builtin-function-split>` function as an example, it can be called with up to 3 arguments.
The first is required while the second two are optional. The ``split`` symbol requires the ``$`` prefix to access the
builtin value.

.. code-block::

  # only the required argument performs an unlimited number of splits on spaces
  $split("Star Wars")         # => ("Star", "Wars")

  # the optional second argument specifies an alternative string to split on
  $split("Star Wars", "r")    # => ('Sta', ' Wa', 's')

  # the optional third argument specifies the maximum number of times to split the string
  $split("Star Wars", "r", 1) # => ('Sta', ' Wars')

  # raises FunctionCallError because the second argument must be a string, the third argument
  # can not be specified without the second
  $split("Star Wars", 1)      # => FunctionCallError: data type mismatch (argument #2)
  $split("Star Wars", ' ', 1) # => ("Star", "Wars")

Reserved Keywords
^^^^^^^^^^^^^^^^^
The following keywords are reserved and can not be used as the names of symbols.

+-----------+-----------------------------------------------------------------+
| Keyword   | Description                                                     |
+-----------+-----------------------------------------------------------------+
| ``null``  | The :py:class:`~ast.NullExpression` literal value               |
+-----------+-----------------------------------------------------------------+
| **Array Comprehension**                                                     |
+-----------+-----------------------------------------------------------------+
| ``for``   | Array comprehension result and assignment delimiter             |
+-----------+-----------------------------------------------------------------+
| ``if``    | Array comprehension iterable and (optional) condition delimiter |
+-----------+-----------------------------------------------------------------+
| **Booleans** (:py:class:`~ast.BooleanExpression` Literals)                  |
+-----------+-----------------------------------------------------------------+
| ``true``  | The "True" boolean value                                        |
+-----------+-----------------------------------------------------------------+
| ``false`` | The "False" boolean value                                       |
+-----------+-----------------------------------------------------------------+
| **Floats** (:py:class:`~ast.FloatExpression` Literals)                      |
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
:py:attr:`~.DataType.DATETIME`, :py:attr:`~.DataType.STRING`, and :py:attr:`TIMEDELTA` literal values are specified in a
very similar manner by defining the value as a string of characters enclosed in either single or double quotes. The
difference comes in an optional leading character before the opening quote. Either no leading character or a single
``s`` will specify a standard :py:attr:`~.DataType.STRING` value, while a single ``d`` will specify a
:py:attr:`~.DataType.DATETIME` value, and a single ``t`` will specify a :py:attr:`~.DataType.TIMEDELTA` value.

.. _literal-datetime-values:

Literal DATETIME Values
"""""""""""""""""""""""

:py:attr:`~.DataType.DATETIME` literals must be specified in ISO-8601 format. The underlying parsing logic is provided
by :py:meth:`dateutil.parser.isoparse`. :py:attr:`~.DataType.DATETIME` values with no time specified (e.g.
``d"2019-09-23"``) will evaluate to a :py:attr:`~.DataType.DATETIME` of the specified day at exactly midnight.

Example rules showing equivalent literal expressions:

* ``d"2019-09-23" == d"2019-09-23 00:00:00"`` (dates default to midnight unless a time is specified)
* ``d"2019-09-23" == d"2019-09-23 00:00:00-04:00"`` (**only equivalent when the local timezone is EDT**)

.. _literal-float-values:

Literal FLOAT Values
""""""""""""""""""""

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

.. _literal-timedelta-values:

Literal TIMEDELTA Values
""""""""""""""""""""""""

:py:attr:`~.DataType.TIMEDELTA` literals must be specified in a subset of the ISO-8601 format for durations. Everything
except years and months are supported in :py:attr:`~.DataType.TIMEDELTA` values, to match the underlying representation
provided by the Python standard library.

Example rules showing equivalent literal expressions:

* ``t"P1D" == t"PT24H"`` (24 hours in a day)
* ``t"P1D" == t"PT1440M"`` (1,440 minutes in a day)

Comments
^^^^^^^^

A single ``#`` symbol can be used to create a comment in the rule text. The everything after the first ``#`` occurrence
will be ignored.

Example rule containing a comment: ``size == 1 # this is a comment``

.. py:currentmodule:: rule_engine

.. _builtin-symbols:

Builtin Symbols
---------------
The following symbols are provided by default using the :py:meth:`~builtins.Builtins.from_defaults` method. These
symbols can be accessed through the ``$`` prefix, e.g. ``$pi``. The default values can be overridden by defining a
custom subclass of :py:class:`~engine.Context` and setting the :py:attr:`~engine.Context.builtins` attribute.

.. _builtin-functions:

Functions
^^^^^^^^^

.. note::
   The following functions use a pseudo syntax to define their signature for use within rules. The signature is:

   ``functionName(argumentType argumentName, ...) -> returnType``

``abs(FLOAT value) -> FLOAT``

:returns: :py:attr:`~.DataType.FLOAT`
:value: (:py:attr:`~.DataType.FLOAT`) The numeric to get the absolute value of.

Returns the absolute value of *value*.

.. versionadded:: 4.1.0

``all(ARRAY[??] values) -> BOOLEAN``

:returns: :py:attr:`~.DataType.BOOLEAN`
:values: (:py:attr:`~.DataType.ARRAY` of *anything*) An array of values to check.

Returns true if every member of the array argument is truthy. If *values* is empty, the function returns true.

``any(ARRAY[??] values) -> BOOLEAN``

:returns: :py:attr:`~.DataType.BOOLEAN`
:values: (:py:attr:`~.DataType.ARRAY` of *anything*) An array of values to check.

Returns true if any member of the array argument is truthy. If *values* is empty, the function returns false.

``ARRAY[??] filter(FUNCTION function, ARRAY[??] values)``

:returns: :py:attr:`~.DataType.ARRAY` of *anything*
:function: (:py:attr:`~.DataType.FUNCTION`) The function to call on each of the values.
:values: (:py:attr:`~.DataType.ARRAY` of *anything*) The array of values to apply *function* to.

Returns an array containing a subset of members from *values* where *function* returns true.

``ARRAY[??] map(FUNCTION function, ARRAY[??] values)``

:returns: :py:attr:`~.DataType.ARRAY` of *anything*
:function: (:py:attr:`~.DataType.FUNCTION`) The function to call on each of the values.
:values: (:py:attr:`~.DataType.ARRAY` of *anything*) The array of values to apply *function* to.

``max(ARRAY[FLOAT] values) -> FLOAT``

:returns: :py:attr:`~.DataType.FLOAT`
:values: (:py:attr:`~.DataType.ARRAY` of :py:attr:`~.DataType.FLOAT`) An array of values to check.

Returns the largest value from the array of values. If *values* is empty, a :py:exc:`~.errors.FunctionCallError` is
raised.

``min(ARRAY[FLOAT] values) -> FLOAT``

:returns: :py:attr:`~.DataType.FLOAT`
:values: (:py:attr:`~.DataType.ARRAY` of :py:attr:`~.DataType.FLOAT`) An array of values to check.

Returns the smallest value from the array of values. If *values* is empty, a :py:exc:`~.errors.FunctionCallError` is
raised.

``parse_datetime(STRING value) -> DATETIME``

:returns: :py:attr:`~.DataType.DATETIME`
:value: (:py:attr:`~.DataType.STRING`) The string value to parse into a timestamp.

Parses the string value into a :py:attr:`~.DataType.DATETIME` value. The string must be in ISO-8601 format and if it
fails to parse, a :py:exc:`~.errors.DatetimeSyntaxError` is raised.

``parse_float(STRING value) -> FLOAT``

:returns: :py:attr:`~.DataType.FLOAT`
:value: (:py:attr:`~.DataType.STRING`) The string value to parse into a numeric.

Parses the string value into a :py:attr:`~.DataType.FLOAT` value. The string must be properly formatted and if it
fails to parse, a :py:exc:`~.errors.FloatSyntaxError` is raised.

``parse_timedelta(STRING value) -> FLOAT``

:returns: :py:attr:`~.DataType.TIMEDELTA`
:value: (:py:attr:`~.DataType.STRING`) The string value to parse into a time period.

Parses the string value into a :py:attr:`~.DataType.TIMEDELTA` value. The string must be properly formatted and if it
fails to parse, a :py:exc:`~.errors.TimedeltaSyntaxError` is raised.

``random([FLOAT boundary]) -> FLOAT``

:returns: :py:attr:`~.DataType.FLOAT`
:boundary: (Optional :py:attr:`~.DataType.FLOAT`) The upper boundary to generate a random number for.

Generate a random number. If *boundary* is not specified, the random number  returned will be between 0 and 1. If
*boundary* is specified, it must be a natural number and the random number returned will be between 0 and *boundary*,
including *boundary*.

``ARRAY[FLOAT] range(FLOAT start, [FLOAT stop, FLOAT step])``

:returns: :py:attr:`~.DataType.ARRAY` of :py:attr:`~.DataType.FLOAT`
:start: (:py:attr:`~.DataType.FLOAT`) The value of the start parameter.
:stop: (Optional :py:attr:`~.DataType.FLOAT`) The value of the stop parameter. If not supplied, start value will be used
    as stop instead.
:step: (Optional :py:attr:`~.DataType.FLOAT`) The value of the step parameter (or 1 if the parameter was not supplied).

Generate a sequence of :py:attr:`~.DataType.FLOAT`'s between *start* (inclusive) and *stop* (exclusive) by *step*.

.. _builtin-function-split:

``ARRAY[STRING] split(STRING string, [STRING sep, FLOAT maxsplit])``

:returns: :py:attr:`~.DataType.ARRAY` of :py:attr:`~.DataType.STRING`
:string: (:py:attr:`~.DataType.STRING`) The string value to split into substrings.
:sep: (Optional :py:attr:`~.DataType.STRING`) The value to split *string* on.
:maxsplit: (Optional :py:attr:`~.DataType.FLOAT`) The maximum number of times tp split *string*.

Split a string value into sub strings. If *sep* is not specified, the *string* will be split by all whitespace. If *sep*
is specified, *string* will be split by that value. This alters how consecutive spaces are handled. When *sep* is not
specified, consecutive whitespace is handled as a single unit and reduced, where as if *sep* is a single space,
consecutive spaces will result in empty strings being returned.

For example:

.. code-block::

  $split("A    B")      # => ('A', 'B')
  $split("A    B", ' ') # => ('A', '', '', '', 'B')

If *maxsplit* is specified, it must be a natural number and will be used as the maximum number of times to split
*string*. This will guarantee that the resulting array length is less than or equal to *maxsplit* + 1.

``sum(ARRAY[FLOAT] values) -> FLOAT``

:returns: :py:attr:`~.DataType.FLOAT`
:values: (:py:attr:`~.DataType.ARRAY` of :py:attr:`~.DataType.FLOAT`) An array of values to add.

Returns the sum of an array of values. If *values* is empty, the function returns 0.

Math Related
^^^^^^^^^^^^

* ``e`` (type: :py:attr:`~.DataType.FLOAT`) -- The mathematical constant *e* (2.71828...).
* ``pi`` (type: :py:attr:`~.DataType.FLOAT`) -- The mathematical constant *pi* (3.14159...).

Regular Expression Related
^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``re_groups`` (type: :py:attr:`~.DataType.ARRAY`) -- An array of strings from the last regular expression match as
  defined by the regular expression itself. See documentation on `grouping`_ for more information. If no match has taken
  place, this value is :py:attr:`~.DataType.NULL`.

  .. note:: For technical reasons, this symbol is provided by the default :py:attr:`~engine.Context` and is not included
    within the :py:meth:`~engine.Builtins.from_defaults`. This means that unlike the other symbols listed here, it will
    be unavailable if the default builtins are replaced.

Timestamp Related
^^^^^^^^^^^^^^^^^

* ``now`` (type: :py:attr:`~.DataType.DATETIME`) -- The current timestamp (including time) using the default timezone
  from :py:attr:`~engine.Context.default_timezone`.
* ``today`` (type: :py:attr:`~.DataType.DATETIME`) -- The current timestamp, (excluding time, normalized to midnight
  00:00:00) using the default timezone from :py:attr:`~engine.Context.default_timezone`.

.. _grouping: https://docs.python.org/3/howto/regex.html#grouping
.. _Order of operations: https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
.. _technique used by Python: https://docs.python.org/3/tutorial/datastructures.html#comparing-sequences-and-other-types
