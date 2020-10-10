.. py:currentmodule:: rule_engine

Data Attributes
===============
The attribute operator (``.``) can be used to recursively resolve values from a
compound native Python data type such as an object or dictionary. This can be
used when the **thing** which the rule is evaluating has members with their own
submembers. If the resolver function fails, the attribute will be checked to
determine if it is a builtin attribute.

.. _builtin-attributes:

Builtin Attributes
------------------
The following attributes are builtin to the default :py:class:`~.Context`
object.

+-----------------+-------------------------------------+
| Attribute Name  | Attribute Type                      |
+-----------------+-------------------------------------+
| :py:attr:`~.DataType.ARRAY` **Attributes**            |
+-----------------+-------------------------------------+
| ``is_empty``    | :py:attr:`~.DataType.BOOLEAN`       |
+-----------------+-------------------------------------+
| ``length``      | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| :py:attr:`~.DataType.DATETIME` **Attributes**         |
+-----------------+-------------------------------------+
| ``date``        | :py:attr:`~.DataType.DATETIME`      |
+-----------------+-------------------------------------+
| ``day``         | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``hour``        | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``microsecond`` | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``millisecond`` | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``minute``      | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``month``       | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``second``      | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``weekday``     | :py:attr:`~.DataType.STRING`        |
+-----------------+-------------------------------------+
| ``year``        | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``zone_name``   | :py:attr:`~.DataType.STRING`        |
+-----------------+-------------------------------------+
| :py:attr:`~.DataType.STRING` **Attributes**           |
+-----------------+-------------------------------------+
| ``as_lower``    | :py:attr:`~.DataType.STRING`        |
+-----------------+-------------------------------------+
| ``as_upper``    | :py:attr:`~.DataType.STRING`        |
+-----------------+-------------------------------------+
| ``to_ary``      | :py:attr:`~.DataType.ARRAY`         |
+-----------------+-------------------------------------+
| ``to_flt``      | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``to_int``      | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
| ``is_empty``    | :py:attr:`~.DataType.BOOLEAN`       |
+-----------------+-------------------------------------+
| ``length``      | :py:attr:`~.DataType.FLOAT`         |
+-----------------+-------------------------------------+
