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
| :py:attr:`~DataType.NULLABLE` | *inner type* or               |
|                               | :py:class:`NoneType`          |
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

.. _data-types-object:

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

Use :py:meth:`DataType.OBJECT.reference` to create a forward-reference placeholder inside an attribute schema.
Self-references are resolved automatically at construction. For self-references, :py:attr:`DataType.OBJECT.self` is
a shorthand sentinel that avoids repeating the enclosing schema's name:

.. code-block:: python

   Hero = rule_engine.DataType.OBJECT('Hero', attributes={
       'name': rule_engine.DataType.STRING,
       'nemesis': rule_engine.DataType.OBJECT.self,  # resolved to Hero
   })

For mutually-recursive types, place both types in the ``type_resolver`` dict and the references will be resolved lazily
at rule parse time:

.. code-block:: python

   Person = rule_engine.DataType.OBJECT('Person', attributes={
       'name': rule_engine.DataType.STRING,
       'employer': rule_engine.DataType.OBJECT.reference('Company'),
   })
   Company = rule_engine.DataType.OBJECT('Company', attributes={
       'name': rule_engine.DataType.STRING,
       'ceo': rule_engine.DataType.OBJECT.reference('Person'),
   })

   context = rule_engine.Context(type_resolver={
       'employee': Person,
       'Person': Person,
       'Company': Company,
   })
   rule = rule_engine.Rule('employee.employer.ceo.name == "Palpatine"', context=context)

From a Dataclass
^^^^^^^^^^^^^^^^

When the source data is already modeled as a Python :py:func:`~dataclasses.dataclass`, the schema can be derived
directly from the field annotations using :py:meth:`DataType.OBJECT.from_dataclass`:

.. code-block:: python

   import dataclasses
   import datetime
   import typing
   import rule_engine

   @dataclasses.dataclass
   class Hero:
       name: str
       publisher: str
       first_appearance: datetime.datetime
       sidekick: typing.Optional[str] = None

   HeroType = rule_engine.DataType.OBJECT.from_dataclass('Hero', Hero)

The derived schema reflects three behaviors automatically:

- **Optional / nullability**: a field annotated as :py:class:`~typing.Optional` (or ``T | None``) produces a
  :py:attr:`~DataType.NULLABLE`-wrapped attribute type in the resulting schema; non-Optional fields are stored
  unwrapped. See :ref:`the NULLABLE section<data-types-nullable>` for how to work with nullable attributes in rules.
- **Nested dataclasses**: a field whose annotation is itself a dataclass becomes a nested ``OBJECT`` (recursively).
  Generic containers (e.g. ``list[Address]``, ``dict[str, Address]``) are walked so nested dataclasses inside
  ``ARRAY``, ``SET``, and ``MAPPING`` types are also expanded.
- **Self and mutual recursion**: a field whose annotation refers back to the enclosing dataclass becomes
  :py:attr:`DataType.OBJECT.self`; cycles between sibling dataclasses produce
  :py:meth:`DataType.OBJECT.reference` placeholders that resolve at rule parse time when both schemas are reachable
  through the :py:class:`~rule_engine.engine.Context` ``type_resolver``.

By default (``strict=True``) a field whose annotation cannot be mapped to a Rule Engine data type raises
:py:exc:`ValueError` so the schema mistake is caught early. Pass ``strict=False`` to instead map the offending
field to :py:attr:`~DataType.UNDEFINED`, leaving it selectable but not type-checked at parse time.

For the common case of building a :py:class:`~rule_engine.engine.Context` directly from a dataclass, the
:py:func:`~rule_engine.engine.type_resolver_from_dataclass` helper produces a resolver whose top-level fields are the
dataclass's own attributes and whose nested ``OBJECT`` types are reachable by name. See
:ref:`getting-started-types-from-dataclass` for an end-to-end example.

From a SQLAlchemy Model
^^^^^^^^^^^^^^^^^^^^^^^

Projects that already model their data with `SQLAlchemy <https://www.sqlalchemy.org/>`_ can derive a schema directly
from a mapped class using :py:meth:`DataType.OBJECT.from_sqlalchemy`. SQLAlchemy is an *optional* dependency; it is
only needed when this entry point is actually invoked. Install it with ``pip install "sqlalchemy>=2.0"``.

.. code-block:: python

   import datetime
   from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
   import rule_engine

   class Base(DeclarativeBase):
       pass

   class Hero(Base):
       __tablename__ = 'heroes'
       id: Mapped[int] = mapped_column(primary_key=True)
       name: Mapped[str]
       alias: Mapped[str | None]
       first_appearance: Mapped[datetime.datetime]
       active: Mapped[bool]

   HeroType = rule_engine.DataType.OBJECT.from_sqlalchemy('Hero', Hero)

The walker reads ``column.type.python_type`` for each mapped column and threads it through
:py:meth:`DataType.from_type`. Column nullability (``column.nullable``) is copied through to the schema's
per-attribute nullability map. :py:class:`~sqlalchemy.Enum` columns become ``STRING`` unless the enum class is an
:py:class:`int` subclass (such as :py:class:`~enum.IntEnum`), in which case they become ``FLOAT`` to match the
integer values stored at runtime. :py:class:`~sqlalchemy.ARRAY` columns become ``ARRAY(T)`` where ``T`` is the
mapped element type (``ARRAY(UNDEFINED)`` when the element type is itself unmappable under ``strict=False``).
:py:class:`~sqlalchemy.JSON` columns report ``dict`` as their ``python_type`` and therefore map to
``MAPPING(UNDEFINED, UNDEFINED)`` in both strict and non-strict mode; the nested keys and values remain untyped.
By default (``strict=True``) a
column whose ``python_type`` raises :py:exc:`NotImplementedError` or resolves to a Python type Rule Engine cannot map
(e.g. :py:class:`~uuid.UUID`) raises :py:exc:`ValueError`. Pass ``strict=False`` to instead map those columns to
:py:attr:`~DataType.UNDEFINED`; this is usually the right choice for schemas that include dialect-specific types
whose values can not be statically described.

Relationships expand automatically:

- ``uselist`` collections (``one-to-many`` / ``many-to-many``) become :py:attr:`DataType.ARRAY` wrapped around the
  target class's ``OBJECT`` and are always non-nullable on the parent (an empty list represents "no items").
- Scalar relationships (``many-to-one`` / ``one-to-one``) become a nested ``OBJECT`` whose nullability is derived
  from the local foreign-key columns.
- Self-references and cycles are detected during the walk: a relationship back to the root class becomes
  :py:attr:`DataType.OBJECT.self`; a relationship back to another ancestor on the build stack becomes a
  :py:meth:`DataType.OBJECT.reference` placeholder that resolves at rule parse time via the
  :py:class:`~rule_engine.engine.Context` ``type_resolver``.

For the common case of building a :py:class:`~rule_engine.engine.Context` directly from a mapped class, the
:py:func:`~rule_engine.engine.type_resolver_from_sqlalchemy` helper produces a resolver whose top-level symbols
are the root class's columns and relationships and whose nested ``OBJECT`` schemas are reachable by name. See
:ref:`getting-started-types-from-sqlalchemy` for an end-to-end example.

Polymorphic / inherited mappings, hybrid properties, and ``column_property`` aggregates are out of scope; only
mapped :py:class:`~sqlalchemy.Column` entries and ``mapper.relationships`` are walked. ``column_property`` entries
that surface in ``mapper.columns`` are silently skipped since they do not expose the metadata the walker needs.

Restrictions
^^^^^^^^^^^^

- Item access on an ``OBJECT`` is a parse-time error. Use ``obj.attribute`` instead of ``obj["attribute"]``.
- Containment checks (``"name" in obj``) are rejected at parse time.
- ``SET(OBJECT(...))`` is rejected at construction because ``OBJECT`` values are not guaranteed to be hashable.
  Use ``ARRAY(OBJECT(...))`` instead.
- ``OBJECT`` types are not inferred by :py:meth:`~DataType.from_value`. They must be annotated explicitly via the
  ``type_resolver``.

NULLABLE
--------

.. _data-types-nullable:

.. versionadded:: 5.0.0

:py:attr:`~DataType.NULLABLE` is a one-argument type constructor that wraps another data type to mark a slot as
permitting :py:class:`NoneType` (``null``) at runtime. ``NULLABLE(T)`` is structurally distinct from both ``T`` and
:py:attr:`~DataType.NULL` and is the single source of truth for nullability in the rule engine's type system.

``NULLABLE`` is produced automatically wherever the source of a type annotation declares optionality:

- :py:meth:`DataType.from_type` maps Python's ``Optional[T]`` / ``T | None`` to ``NULLABLE(from_type(T))``.
- :py:meth:`DataType.OBJECT.from_dataclass` wraps attribute types for dataclass fields typed as ``Optional[T]`` and
  for nested dataclass fields that can hold ``None``.
- :py:meth:`DataType.OBJECT.from_sqlalchemy` wraps attribute types for columns whose ``nullable`` is ``True``, and for
  scalar relationships whose local foreign-key columns are nullable.
- Compound element types (``ARRAY``, ``SET``, ``MAPPING`` values) store ``NULLABLE(T)`` directly when the member may
  be ``None``.

Semantics are Python-style, not SQL three-valued logic. ``None`` flows through expressions as the Python ``None``
value. Parse-time checking is strict: operators that do not meaningfully accept ``None`` — arithmetic (``+``, ``-``,
``*``, ``/``, …), ordered comparisons (``<``, ``<=``, ``>``, ``>=``), the regex operators (``=~``, ``=~~``, ``!~``,
``!~~``), bitwise and bitwise-shift operators, unary minus, containment (``x in container``), attribute access
(``obj.attr``), item access (``container[key]``), slicing (``container[a:b]``), and function arguments — reject a
``NULLABLE(T)`` operand at parse time with an :py:exc:`~rule_engine.errors.EvaluationError` (or
:py:exc:`~rule_engine.errors.FunctionCallError` for function arguments) whose message points at the discharge
operators. The rule does not parse; the author must discharge nullability first.

Operators that are meaningful on ``None`` stay lenient: equality and logical connectives (``==``, ``!=``, ``and``,
``or``, ``not``) always accept ``NULLABLE`` operands and return plain :py:attr:`~DataType.BOOLEAN`; ternary
expressions (``cond ? a : b``) propagate ``NULLABLE`` to the result if either branch is nullable; and safe-navigation
operators accept ``NULLABLE`` targets by design.

The grammar exposes two mechanisms for working with nullable values:

- ``left ?? right`` (null-coalesce) — *discharges* ``NULLABLE``. Evaluates to ``left`` when it is not ``None``, else
  ``right``. The result type is the peeled type of the left operand, re-wrapped in ``NULLABLE`` only if the right
  operand is itself nullable or is the ``null`` literal.
- Safe attribute access (``obj&.attr``) and safe item access (``container&[key]``) — *accept* a ``NULLABLE`` target
  without raising but do not discharge it. The overall expression remains nullable, so chaining
  ``obj&.inner&.leaf`` yields a ``NULLABLE`` value that a downstream operator must still discharge.

A few Python-style edge cases worth knowing:

- A ``NULLABLE(BOOLEAN)`` value used as a ternary condition (``flag ? x : y``) is accepted at parse time. ``None``
  is falsy, so a null condition evaluates the false branch at runtime.
- ``not NULLABLE(BOOLEAN)`` is accepted and returns plain ``BOOLEAN``. ``not None`` evaluates to ``True``.
- ``NULLABLE(T) in container`` (nullable *member*, non-nullable container) is accepted. ``None in [...]`` returns
  ``False``, consistent with Python.
- ``non_nullable_value ?? null`` gives a ``NULLABLE`` result type. The static analysis conservatively wraps the
  result whenever the right operand is ``null``, even if the left can never be ``None`` at runtime.

The legacy ``attributes_nullable`` / ``value_type_nullable`` kwargs on :py:class:`~DataType.OBJECT` and compound-type
constructors are still accepted in v5 for backward compatibility but emit a :py:class:`DeprecationWarning` and will
be removed in v6.0. Wrap the attribute or element type in :py:attr:`~DataType.NULLABLE` directly instead.

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
