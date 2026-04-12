.. py:currentmodule:: rule_engine.types

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
| :py:attr:`~DataType.BYTES`    | :py:class:`bytes`             |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.DATETIME` | :py:class:`datetime.date`,    |
|                               | :py:class:`datetime.datetime` |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.FLOAT`    | :py:class:`int`,              |
|                               | :py:class:`float`             |
|                               | :py:class:`decimal.Decimal`   |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.FUNCTION` | *anything callable*           |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.MAPPING`  | :py:class:`dict`              |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.NULL`     | :py:class:`NoneType`          |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.OBJECT`   | *any* (schema-driven)         |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.SET`      | :py:class:`set`               |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.STRING`   | :py:class:`str`               |
+-------------------------------+-------------------------------+
| :py:attr:`~DataType.TIMEDELTA`| :py:class:`datetime.timedelta`|
+-------------------------------+-------------------------------+

Compound Types
--------------
The compound data types (:py:attr:`~DataType.ARRAY`, :py:attr:`~DataType.SET`, and :py:attr:`~DataType.MAPPING`) are all
capable of containing zero or more values of other data types (though it should be noted that
:py:attr:`~DataType.MAPPING` keys **must be scalars** while the values can be anything). The member types of compound
data types can be defined, but only if the members are all of the same type. For an example, an array containing floats
can be defined, and an mapping with string keys to string values can also be defined, but a mapping with string keys to
values that are either floats, strings or booleans **may not be completely defined**. For more information, see the
section on :ref:`getting-started-compound-data-types` in the Getting Started page.

Compound data types are also iterable, meaning that array comprehension operations can be applied to them. Iteration
operations apply to the members of :py:attr:`~DataType.ARRAY` and :py:attr:`~DataType.SET` values, and the keys of
:py:attr:`~DataType.MAPPING` values. This allows the types to behave in the same was as they do in Python.

OBJECT
------

.. versionadded:: 5.0.0

The :py:attr:`~DataType.OBJECT` type represents a user-defined schema with named, typed attributes. Unlike
:py:attr:`~DataType.MAPPING`, which is keyed by arbitrary values, an ``OBJECT`` has a fixed set of attributes known at
rule parse time. This enables parse-time validation: accessing an unknown attribute raises an
:py:class:`~rule_engine.errors.ObjectAttributeError` with a suggestion, and item access (``obj["name"]``) is rejected
outright.

Defining an Object Type
^^^^^^^^^^^^^^^^^^^^^^^

An ``OBJECT`` type is created by calling :py:attr:`~DataType.OBJECT` with a name and an attribute schema:

.. code-block:: python

   import rule_engine

   Hero = rule_engine.DataType.OBJECT('Hero', attributes={
       'name': rule_engine.DataType.STRING,
       'publisher': rule_engine.DataType.STRING,
       'first_appearance': rule_engine.DataType.DATETIME,
   })

The *name* is used for nominal type compatibility: two ``OBJECT`` types are compatible only when their names match.

Custom Accessors
^^^^^^^^^^^^^^^^

By default, attribute values are fetched with :py:func:`getattr`. A custom *accessor* can be provided to support other
backing stores (dictionaries, database rows, etc.):

.. code-block:: python

   # use a dict-backed object instead of an attribute-backed one
   Hero = rule_engine.DataType.OBJECT('Hero',
       attributes={'name': rule_engine.DataType.STRING},
       accessor=lambda obj, name: obj[name]
   )

Forward References and Recursion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :py:meth:`DataType.reference` to create a forward-reference placeholder inside an attribute schema.
Self-references are resolved automatically at construction:

.. code-block:: python

   Hero = rule_engine.DataType.OBJECT('Hero', attributes={
       'name': rule_engine.DataType.STRING,
       'nemesis': rule_engine.DataType.reference('Hero'),  # resolved to Hero
   })

For mutually-recursive types, place both types in the ``type_resolver`` dict and the references will be resolved lazily
at rule parse time:

.. code-block:: python

   Person = rule_engine.DataType.OBJECT('Person', attributes={
       'name': rule_engine.DataType.STRING,
       'employer': rule_engine.DataType.reference('Company'),
   })
   Company = rule_engine.DataType.OBJECT('Company', attributes={
       'name': rule_engine.DataType.STRING,
       'ceo': rule_engine.DataType.reference('Person'),
   })

   context = rule_engine.Context(type_resolver={
       'employee': Person,
       'Person': Person,
       'Company': Company,
   })
   rule = rule_engine.Rule('employee.employer.ceo.name == "Palpatine"', context=context)

Restrictions
^^^^^^^^^^^^

- Item access on an ``OBJECT`` is a parse-time error. Use ``obj.attribute`` instead of ``obj["attribute"]``.
- Containment checks (``"name" in obj``) are rejected at parse time.
- ``SET(OBJECT(...))`` is rejected at construction because ``OBJECT`` values are not guaranteed to be hashable.
  Use ``ARRAY(OBJECT(...))`` instead.
- ``OBJECT`` types are not inferred by :py:meth:`~DataType.from_value`. They must be annotated explicitly via the
  ``type_resolver``.

FLOAT
-----
See :ref:`literal-float-values` for syntax.

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
are converted to Rule Engine :py:attr:`~DataType.MAPPING` values. While in Python the value
``{0.1: 'a', Decimal('0.1'): 'a'}`` would have a length of 2 with two unique keys, the same value once converted into a
Rule Engine :py:attr:`~DataType.MAPPING` would have a length of 1 with a single unique key. For this reason, developers
using Rule Engine should take care to not use compound data types with a mix of Python :py:class:`float` and
:py:class:`~decimal.Decimal` values.

FUNCTION
--------
Version :release:`4.0.0` added the :py:attr:`~DataType.FUNCTION` datatype. This can be used to make functions available
to rule authors. Rule Engine contains a few :ref:`builtin functions<builtin-functions>` that can be used by default.
Additional functions must be defined in Python and can either be added to the evaluated object or by
:ref:`extending the builtin symbols<changing-builtin-symbols>`. It is only possible to call a function from within the
rule text. Functions can not be defined by rule authors as other data types can be.

TIMEDELTA
---------
See :ref:`literal-timedelta-values` for syntax.

Version :release:`3.5.0` introduced the :py:attr:`~DataType.TIMEDELTA` datatype, backed by Python's
:py:class:`~datetime.timedelta` class. This also comes with the ability to perform arithmetic with both
:py:attr:`~DataType.TIMEDELTA` *and* :py:attr:`~DataType.DATETIME` values. This allows you to create rules for things
such as "has it been 30 days since this thing happened?" or "how much time passed between two events?".

The following mathematical operations are supported:

* Adding a timedelta to a datetime (result is a datetime)
* Adding a timedelta to another timedelta (result is a timedelta)
* Subtracting a timedelta from a datetime (result is a datetime)
* Subtracting a datetime from another datetime (result is a timedelta)
* Subtracting a timedelta from another timedelta (result is a timedelta)
