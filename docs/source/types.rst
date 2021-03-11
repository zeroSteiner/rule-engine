.. py:currentmodule:: rule_engine

Data Types
==========
The following table describes the data types supported by the Rule Engine and the Python data types that each is
compatible with. For a information regarding supported operations, see the
:ref:`Supported Operations<data-type-operations>` table.

.. _data-types:

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
|                               | :py:class:`decimal.Decimal`   |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.MAPPING`  | :py:class:`dict`              |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.NULL`     | :py:class:`NoneType`          |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.STRING`   | :py:class:`str`               |
+-------------------------------+-------------------------------+

FLOAT
-----
Starting in :release:`3.0.0`, the ``FLOAT`` datatype is backed by Python's :py:class:`~decimal.Decimal` object. This
makes the evaluation of arithmetic more intuitive for the audience of rule authors who are not assumed to be familiar
with the nuances of binary floating point arithmetic. To take an example from the :py:mod:`decimal` documentation, rule
authors should not have to know that ``0.1 + 0.1 + 0.1 - 0.3 != 0``.

Internally, Rule Engine conversion values from Python :py:class:`float` and :py:class:`int` objects to
:py:class:`~decimal.Decimal` using their string representation (as provided by :py:func:`repr`) **and not**
:py:meth:`~decimal.Decimal.from_float`. This is to ensure that a Python :py:class:`float` value of ``0.1`` that is
provided by an input will match a Rule Engine literal of ``0.1``. To explicitly pass a binary floating point value, the
caller must convert it using :py:meth:`~decimal.Decimal.from_float` themselves. To change the behavior of the floating
point arithmetic, a :py:class:`decimal.Context` can be specified by the :py:class:`~rule_engine.engine.Context` object.

Since Python's :py:class:`~decimal.Decimal` values are not always equivalent to themselves (e.g.
``0.1 != Decimal('0.1')``) it's important to know that Rule Engine will coerce and normalize these values. That means
that while in Python ``0.1 in [ Decimal('0.1') ]`` will evaluate to ``False``, in a rule it will evaluate to ``True``
(e.g. ``Rule('0.1 in numbers').evaluate({'numbers': [Decimal('0.1')]})``). This also affects Python dictionaries that
are converted to Rule Engine ``MAPPING`` values. While in Python the value ``{0.1: 'a', Decimal('0.1'): 'a'}`` would
have a length of 2 with two unique keys, the same value once converted into a Rule Engine ``MAPPING`` would have a
length of 1 with a single unique key. For this reason, developers using Rule Engine should take care to not use compound
data types with a mix of Python :py:class:`float` and :py:class:`~decimal.Decimal` values.