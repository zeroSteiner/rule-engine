.. py:currentmodule:: rule_engine

Data Attributes
===============
The attribute operator (``.``) can be used to recursively resolve values from a compound native Python data type such as
an object or dictionary. This can be used when the **thing** which the rule is evaluating has members with their own
submembers. If the resolver function fails, the attribute will be checked to determine if it is a builtin attribute.

.. _builtin-attributes:

Builtin Attributes
------------------
The following attributes are builtin to the default :py:class:`~.Context` object.

+-------------------------+-----------------------------------------------+
| Attribute Name          | Attribute Type                                |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.ARRAY` **Attributes**                              |
+-------------------------+-----------------------------------------------+
| ``ends_with(prefix)``   | :ref:`FUNCTION<builtin-method-ends-with>`     |
+-------------------------+-----------------------------------------------+
| ``is_empty``            | :py:attr:`~.DataType.BOOLEAN`                 |
+-------------------------+-----------------------------------------------+
| ``length``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``starts_with(prefix)`` | :ref:`FUNCTION<builtin-method-starts-with>`   |
+-------------------------+-----------------------------------------------+
| ``to_ary``              | :py:attr:`~.DataType.ARRAY`                   |
+-------------------------+-----------------------------------------------+
| ``to_set``              | :py:attr:`~.DataType.SET`                     |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.BYTES` **Attributes**                              |
+-------------------------+-----------------------------------------------+
| ``ends_with(prefix)``   | :ref:`FUNCTION<builtin-method-ends-with>`     |
+-------------------------+-----------------------------------------------+
| ``is_empty``            | :py:attr:`~.DataType.BOOLEAN`                 |
+-------------------------+-----------------------------------------------+
| ``length``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``starts_with(prefix)`` | :ref:`FUNCTION<builtin-method-starts-with>`   |
+-------------------------+-----------------------------------------------+
| ``to_ary``              | :py:attr:`~.DataType.ARRAY`                   |
+-------------------------+-----------------------------------------------+
| ``to_set``              | :py:attr:`~.DataType.SET`                     |
+-------------------------+-----------------------------------------------+
| ``decode(encoding)``    | :ref:`FUNCTION<builtin-method-decode>`        |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.DATETIME` **Attributes**                           |
+-------------------------+-----------------------------------------------+
| ``date``                | :py:attr:`~.DataType.DATETIME`                |
+-------------------------+-----------------------------------------------+
| ``day``                 | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``hour``                | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``microsecond``         | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``millisecond``         | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``minute``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``month``               | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``second``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``to_epoch``            | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``weekday``             | :py:attr:`~.DataType.STRING`                  |
+-------------------------+-----------------------------------------------+
| ``year``                | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``zone_name``           | :py:attr:`~.DataType.STRING`                  |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.FLOAT` **Attributes** :sup:`1`                     |
+-------------------------+-----------------------------------------------+
| ``ceiling``             | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``floor``               | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``is_nan``              | :py:attr:`~.DataType.BOOLEAN`                 |
+-------------------------+-----------------------------------------------+
| ``to_flt``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``to_str``              | :py:attr:`~.DataType.STRING`                  |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.MAPPING` **Attributes**                            |
+-------------------------+-----------------------------------------------+
| ``is_empty``            | :py:attr:`~.DataType.BOOLEAN`                 |
+-------------------------+-----------------------------------------------+
| ``keys``                | :py:attr:`~.DataType.ARRAY`                   |
+-------------------------+-----------------------------------------------+
| ``length``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``values``              | :py:attr:`~.DataType.ARRAY`                   |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.SET` **Attributes**                                |
+-------------------------+-----------------------------------------------+
| ``is_empty``            | :py:attr:`~.DataType.BOOLEAN`                 |
+-------------------------+-----------------------------------------------+
| ``length``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``to_ary``              | :py:attr:`~.DataType.ARRAY`                   |
+-------------------------+-----------------------------------------------+
| ``to_set``              | :py:attr:`~.DataType.SET`                     |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.STRING` **Attributes**                             |
+-------------------------+-----------------------------------------------+
| ``as_lower``            | :py:attr:`~.DataType.STRING`                  |
+-------------------------+-----------------------------------------------+
| ``as_upper``            | :py:attr:`~.DataType.STRING`                  |
+-------------------------+-----------------------------------------------+
| ``encode(encoding)``    | :ref:`FUNCTION<builtin-method-encode>`        |
+-------------------------+-----------------------------------------------+
| ``ends_with(prefix)``   | :ref:`FUNCTION<builtin-method-ends-with>`     |
+-------------------------+-----------------------------------------------+
| ``to_ary``              | :py:attr:`~.DataType.ARRAY`                   |
+-------------------------+-----------------------------------------------+
| ``to_flt``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``to_set``              | :py:attr:`~.DataType.SET`                     |
+-------------------------+-----------------------------------------------+
| ``to_str``              | :py:attr:`~.DataType.STRING`                  |
+-------------------------+-----------------------------------------------+
| ``to_int``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``is_empty``            | :py:attr:`~.DataType.BOOLEAN`                 |
+-------------------------+-----------------------------------------------+
| ``length``              | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``starts_with(prefix)`` | :ref:`FUNCTION<builtin-method-starts-with>`   |
+-------------------------+-----------------------------------------------+
| :py:attr:`~.DataType.TIMEDELTA` **Attributes**                          |
+-------------------------+-----------------------------------------------+
| ``days``                | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``seconds``             | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``microseconds``        | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+
| ``total_seconds``       | :py:attr:`~.DataType.FLOAT`                   |
+-------------------------+-----------------------------------------------+

FLOAT Attributes :sup:`1`
^^^^^^^^^^^^^^^^^^^^^^^^^
Due to the syntax of floating point literals, the attributes must be accessed using parenthesis. For example
``3.14.to_str`` is invalid while ``(3.14).to_str`` is valid.

Encoding and Decoding
^^^^^^^^^^^^^^^^^^^^^
:py:attr:`~.DataType.BYTES` values can be converted to :py:attr:`~.DataType.STRING` values by calling their ``.decode``
method. :py:attr:`~.DataType.STRING` values can be converted to :py:attr:`~.DataType.BYTES` values by calling their
``.encode`` method. This resembles Python's native functionality and the ``encoding`` argument to each is the same, i.e.
it can be any encoding name that Python can handle such as ``UTF-8``. In addition to the encoding names that Python can
handle, the special names ``hex``, ``base16`` and ``base64`` can be used for transcoding ascii-hex, and base-64
formatted data.

Object Methods
^^^^^^^^^^^^^^
Much like in Python, a method is a function that is associated with an object. They are defined as
:py:attr:`~.DataType.FUNCTION` values and are accessed as attributes.

.. _builtin-method-decode:

``BYTES decode(STRING encoding) -> STRING``

:returns: :py:attr:`~.DataType.STRING`
:encoding: (:py:attr:`~.DataType.STRING`) The encoding name to use.

Returns the decoded value.

.. versionadded:: 4.5.0

.. _builtin-method-encode:

``STRING encode(STRING encoding) -> BYTES``

:returns: :py:attr:`~.DataType.BYTES`
:encoding: (:py:attr:`~.DataType.STRING`) The encoding name to use.

Returns the encoded value.

.. versionadded:: 4.5.0

.. _builtin-method-ends-with:

``ARRAY | BYTES | STRING ends_with(ARRAY | BYTES | STRING suffix) -> BOOLEAN``

:returns: :py:attr:`~.DataType.BOOLEAN`
:suffix: The suffix to check for. The data type must match the object type.

Check whether the value ends with the specified value.

.. versionadded:: 4.5.0

.. _builtin-method-starts-with:

``ARRAY | BYTES | STRING starts_with(ARRAY | BYTES | STRING prefix) -> BOOLEAN``

:returns: :py:attr:`~.DataType.BOOLEAN`
:prefix: The prefix to check for. The data type must match the object type.

Check whether the value starts with the specified value.

.. versionadded:: 4.5.0
