.. py:currentmodule:: rule_engine

Getting Started
===============
The Rule Engine is meant to allow developers to filter arbitrary Python objects with a "rule" specified either by them
or by an end user. The "rules" that the Rule Engine uses are Python string expressions in a custom language. The syntax
that Rule Engine uses is similar to Python but borrows some features from Ruby. The rules are a custom language and no
Python ``exec`` or ``eval`` operations are used, allowing developers to safely and securely evaluate rule expressions
provided by potentially untrusted sources.

Basic Usage
-----------
#. The developer needs to identify data that they would like to be filtered. This would be some kind of object with a
   set of variable attributes. The rest of the usage example will assume that these objects are comic books.

   * Comic books have various attributes that could be useful for filtering including:

      +-----------+-----------------------+-----------------------------------+
      | Attribute | Python Type           | Rule Engine Type                  |
      +-----------+-----------------------+-----------------------------------+
      | title     | ``str``               | :py:attr:`~.DataType.STRING`      |
      +-----------+-----------------------+-----------------------------------+
      | publisher | ``str``               | :py:attr:`~.DataType.STRING`      |
      +-----------+-----------------------+-----------------------------------+
      | issue     | ``int``               | :py:attr:`~.DataType.FLOAT`       |
      +-----------+-----------------------+-----------------------------------+
      | released  | ``datetime.date``     | :py:attr:`~.DataType.DATETIME`    |
      +-----------+-----------------------+-----------------------------------+

   * An example comic book collection might look like:

      .. code-block:: python

         comics = [
           {
             'title': 'Batman',
             'publisher': 'DC',
             'issue': 89,
             'released': datetime.date(2020, 4, 28)
           },
           {
             'title': 'Flash',
             'publisher': 'DC',
             'issue': 753,
             'released': datetime.date(2020, 5, 5)
           },
           {
             'title': 'Captain Marvel',
             'publisher': 'Marvel',
             'issue': 18,
             'released': datetime.date(2020, 5, 6)
           }
         ]

#. Now the developer needs to create a rule object to match the target objects. The attributes of the objects will
   automatically become valid symbols for the rule expression. Creating a rule object is done by initializing an
   instance of the :py:class:`~engine.Rule` class which requires one argument, and that is the string expression (in
   Rule Engine syntax) of the rule.

   * In the case of the comic book collection, these symbols would be: ``title``, ``publisher``, ``issue``, and
     ``released``. Notice that these attribute names are also valid symbol names, i.e. they start with a letter and
     contain no whitespace or punctuation. Just like in Python, Rule Engine symbols must follow these rules. For
     example, ``released`` is a valid symbol while ``Released Date`` is not (because of the space).

   * A simple rule for the comic book collection which matches the ``publisher`` symbol to the string ``"DC"`` might
     look like:

      .. code-block:: python

         rule = rule_engine.Rule(
           # match books published by DC
           'publisher == "DC"'
         )

   * Rules can contain more complex expressions such as datetime literals and conditionals.

      .. code-block:: python

         rule = rule_engine.Rule(
           # match DC books released in May 2020
           'released >= d"2020-05-01" and released < d"2020-06-01" and publisher == "DC"'
         )

      Notice that the datetime expression is a string, prefixed with ``d`` in ``YYYY-MM-DD HH:mm:SS`` format. If the
      time portion is omitted, it will be normalized to ``00:00:00`` (midnight, zero minutes, zero seconds). See the
      :ref:`Literal Values<literal-values>` section for more information.

   * Certain datatypes also have :ref:`attributes<builtin-attributes>` that can be accessed with the dot (``.``)
     operator.

      .. code-block:: python

         rule = rule_engine.Rule(
           # normalize potential variations in the publisher case such as 'Dc'
           'publisher.as_upper == "DC"'
         )

   * Rules can also match strings using regular expressions. When using this type of comparison, the string on the right
     hand side of the operator is the regular expression, while the left is the string to compare it with.

      .. code-block:: python

         rule = rule_engine.Rule(
           # match books with a title starting with 'Captain '
           'title =~ "Captain\s\S+"'
         )

#. Once the rule object has been defined, it can be applied to target object(s). Two primary methods are available for
   applying the rule to the target objects. Those methods are:

   * :py:meth:`~engine.Rule.matches` -- This method will determine whether the rule matches a single target object,
     returning ``True`` or ``False``.
   * :py:meth:`~engine.Rule.filter` -- This method will filter an iterable of target objects, yielding ones for which
     the rule matches.

   * Applying the rule to the comic book collection using each of the two methods might look like:

      .. code-block:: python

         # check if the first object matches
         rule.matches(comics[0]) # => True

         # filter the iterable "comics" and return matching objects
         rule.filter(comics) # => <generator object Rule.filter at 0x7f2bdafbe650>

Attribute-Backed Objects
^^^^^^^^^^^^^^^^^^^^^^^^
In the previous example, the target objects were Python dictionaries. The keys in the dictionary were used as symbols
and while this is the default behavior it can be modified to use object attributes instead. This would be necessary if
the target objects had variable attributes (like a Python class object) instead of variable items (like a Python
dictionary object).

   * An example comic book collection using an object-based attribute-backed data structure might look like:

      .. code-block:: python

         class Comic(object):
             def __init__(self, title, publisher, issue, released)
                 self.title = title
                 self.publisher = publisher
                 self.issue = issue
                 self.released = released

         comics = [
           Comic('Batman',         'DC',     89,  datetime.date(2020, 4, 28)),
           Comic('Flash',          'DC',     753, datetime.date(2020, 4, 28)),
           Comic('Captain Marvel', 'Marvel', 18,  datetime.date(2020, 5, 6))
         ]

To resolve symbols from attributes, a custom :py:class:`~engine.Context` object needs to be defined. This object is used
for configuration of Rule behavior, one setting of which is the resolver to use. The resolver defines how a rule looks
up symbols to their values for comparison given a target object. The following resolver functions are included in Rule
Engine:

* :py:func:`~engine.resolve_attribute` -- Resolve symbols by looking them up as attributes on an object.
* :py:func:`~engine.resolve_item` -- **(Default)** Resolve symbols by looking them up as keys on a dictionary (or
  dictionary-like) object.

To change the resolver, create a :py:class:`~engine.Context` object, and specify the *resolver* function as a keyword
argument.

.. code-block:: python

   # define the custom context to set the resolver
   context = rule_engine.Context(resolver=rule_engine.resolve_attribute)
   # then define a rule using the custom context
   rule = rule_engine.Rule('publisher == "DC"', context=context)

Once the rule has been defined with the custom context, it can be used in the same way as a rule with a default context.
The context object can be shared with other rule objects that are to be applied on the same objects. The context object
should not be shared with rule object that are applied to other objects which do not have the same attributes (like
artists).

.. _getting-started-rule-chains:

Rule Chains
-----------

.. versionadded:: 5.1.0

A :py:class:`~engine.Chain` evaluates an object against an ordered list of rules, each of which is paired with a value,
and returns the value of the first rule that matches. This is modeled after a chain in iptables, where each rule has a
target and a packet stops at the first matching rule with a terminating target such as ``ACCEPT`` or ``DROP``. The
values can be any Python object, such as the members of an :py:class:`~enum.Enum`.

Each rule can be either the text of a rule, which is compiled with the chain's :py:attr:`~engine.Chain.context`, or a
:py:class:`~engine.Rule` instance, which is used as-is and keeps its own context. Like a rule, a chain uses a default
:py:class:`~engine.Context` unless one is specified with the *context* parameter.

.. code-block:: python

   import enum
   import rule_engine

   class Action(enum.Enum):
       ACCEPT = 'accept'
       DROP = 'drop'

   chain = rule_engine.Chain(
       [
           ('source in ["203.0.113.7", "203.0.113.8"]', Action.DROP),
           ('port == 22 and source.starts_with("192.168.")', Action.ACCEPT),
           ('port in [80, 443]', Action.ACCEPT),
       ],
       default_value=Action.DROP
   )

   chain.evaluate({'source': '192.168.1.10', 'port': 22})
   # => <Action.ACCEPT: 'accept'>
   chain.evaluate({'source': '203.0.113.7', 'port': 443})
   # => <Action.DROP: 'drop'>
   chain.evaluate({'source': '198.51.100.1', 'port': 8080})
   # => <Action.DROP: 'drop'>

A rule matches the same way :py:meth:`~engine.Rule.matches` does. Errors that are raised while evaluating a rule, such
as a :py:class:`~errors.SymbolResolutionError` for an object that is missing a symbol, are not caught by the chain.

Chain Default Values
^^^^^^^^^^^^^^^^^^^^
When no rule matches, the chain returns its *default_value*, which serves the same purpose as the policy of an iptables
chain. If no *default_value* is specified, a :py:class:`~errors.ChainExhaustedError` is raised instead. The object that
was evaluated is available from the exception's :py:attr:`~errors.ChainExhaustedError.thing` attribute, but it is not
included in the exception's message.

.. code-block:: python

   chain = rule_engine.Chain([('port == 22', Action.ACCEPT)])
   chain.evaluate({'port': 80})
   # => ChainExhaustedError: no rule in the chain matched and no default value is set

The chain's *default_value* is separate from the :ref:`default value of a context<getting-started-default-value>`. The
chain's default value is used when no rule matches, while the context's default value is used for symbols and attributes
that are missing from the object. To have a rule that refers to a missing symbol evaluate it as ``null`` instead of
raising an exception, use a context with a default value.

.. code-block:: python

   context = rule_engine.Context(default_value=None)
   chain = rule_engine.Chain([('port == 22', Action.ACCEPT)], default_value=Action.DROP, context=context)
   chain.evaluate({})
   # => <Action.DROP: 'drop'>

Modifying A Chain
^^^^^^^^^^^^^^^^^
A chain can be modified after it has been created using methods that are named after the iptables commands. Unlike the
rule numbers used by iptables, indexes start at 0 and negative indexes count from the end of the chain.

* :py:meth:`~engine.Chain.append` -- Add an entry to the end of the chain, like ``iptables --append``.
* :py:meth:`~engine.Chain.insert` -- Insert an entry before an index, like ``iptables --insert``. This follows the
  semantics of :py:meth:`list.insert`, so ``chain.insert(-1, rule, value)`` adds an entry before the last one, which is
  useful for keeping a catch-all rule at the end of the chain.
* :py:meth:`~engine.Chain.delete` -- Remove the entry at an index and return it, like ``iptables --delete``.
* :py:meth:`~engine.Chain.flush` -- Remove every entry, like ``iptables --flush``. The default value is unchanged.

.. code-block:: python

   chain = rule_engine.Chain([('true', Action.DROP)])
   chain.insert(-1, 'port == 443', Action.ACCEPT)
   chain.insert(0, 'source == "203.0.113.7"', Action.DROP)
   [entry.rule.text for entry in chain]
   # => ['source == "203.0.113.7"', 'port == 443', 'true']

A chain can be evaluated by multiple threads while it is being modified. Each evaluation uses the entries that were in
the chain when it started, and modifications made by different threads at the same time are not lost. Because adding or
removing an entry copies the others, a chain with many entries is best created by passing them to the constructor. A
chain should not be modified from a ``__del__`` method or a :py:mod:`weakref` finalizer, because those can run while
another modification is in progress.

Inspecting Matches
^^^^^^^^^^^^^^^^^^
The :py:meth:`~engine.Chain.find` method returns the :py:class:`~engine.ChainEntry` of the first rule that matches,
or ``None`` if none of them do. This can be used to determine which rule was applied, for example to log it. Unlike
:py:meth:`~engine.Chain.evaluate`, the default value is not used. The :py:meth:`~engine.Chain.index` method returns the
position of an entry in the chain.

.. code-block:: python

   chain = rule_engine.Chain([('port == 22', Action.ACCEPT), ('port == 23', Action.DROP)])
   entry = chain.find({'port': 23})
   entry.rule.text
   # => 'port == 23'
   entry.value
   # => <Action.DROP: 'drop'>
   chain.index(entry)
   # => 1

A chain's entries can also be inspected with :py:func:`len`, iteration and indexing. Slicing a chain returns a new chain
with the entries in the slice and the same default value and context as the original, so for example ``chain[:-1]`` is
the chain without its last entry. Adding or removing entries in either chain afterwards does not change the other. Like
other containers, a chain without any entries is falsy, even when it has a default value.

Serialization
^^^^^^^^^^^^^
A chain can be serialized with :py:mod:`pickle` as long as its context, rules and values can be. In the examples above,
``Action`` must be defined at the module level for its members to be pickled. Rules that shared a context before the
chain was pickled continue to share one after it is loaded.

Advanced Usage
--------------
The Rule Engine has a number of advanced features that contribute to its flexibility. In most use cases they are
unnecessary.

.. _getting-started-default-value:

Setting A Default Value
^^^^^^^^^^^^^^^^^^^^^^^
By default, :py:class:`engine.Rule` will raise a :py:class:`~errors.SymbolResolutionError` for invalid symbols. In some
cases, it may be desirable to change the way in which the language behaves to instead treat unknown symbols with a
default value (most often ``None`` / :py:attr:`~.DataType.NULL` is used for this purpose, but any value of a supported
type can be used). To change this behavior, set the *default_value* parameter when initializing the
:py:class:`~engine.Context` instance.

.. code-block:: python

   # this fails because title is not defined and there is no default_value
   rule_engine.Rule('title').matches({})
   # => SymbolResolutionError: title

   context = rule_engine.Context(default_value=None)
   # this evaluates successfully to False because title is null (from the default value)
   rule_engine.Rule('title', context=context).matches({})
   # => False

   # this evaluates successfully to True because title is a non-empty string
   rule_engine.Rule('title', context=context).matches({'title': 'Batman'})
   # => True

Custom Resolvers
^^^^^^^^^^^^^^^^
Rule Engine includes resolvers for accessing attributes :py:func:`as keys<engine.resolve_item>` on objects (such as
dictionaries) and one for resolving symbols :py:func:`as attributes<engine.resolve_attribute>` on objects. If for some
reason, neither of those are suitable for the target object then a custom one can be defined and used.

The custom resolver should use the signature ``resolver(thing, name)`` where *thing* is the arbitrary object that the
rule is being applied to and *name* is the symbol name as a Python string of the attribute that is to be accessed. If
the resolver function fails for any reason, it should raise a :py:class:`~errors.SymbolResolutionError`, forwarding
*thing* in a keyword argument. This ensures consistency in how exceptions are raised and handled by the engine.

Suggestions
"""""""""""
When raising a :py:class:`~errors.SymbolResolutionError`, a custom resolver can optionally make a suggestion for a valid
symbol name. In this case, the resolver may use the :py:class:`~suggestions.suggest_symbol` function, passing it the
invalid name and a list of valid names. The result may then be passed as the *suggestion* keyword. This suggestion may
then assist rule authors in correcting mistakes.

Type Hinting
^^^^^^^^^^^^
Symbol type information can be provided to the :py:class:`~engine.Rule` through the :py:class:`~engine.Context` instance
and will be used for compatibility testing. With type information, the engine will raise an
:py:class:`~errors.EvaluationError` when an incompatible operation is detected such as a regex match (``=~``) using an
integer on either side. This makes it possible to detect errors in a rule's syntax prior to it being applied to an
object. When symbol type information is specified, the value resolved from a symbol and object must either match the
specified type or be :py:attr:`~ast.NULL`, otherwise a :py:class:`~errors.SymbolTypeError` will be raised when the
symbol is resolved.

To define type information, a *type_resolver* function must be passed to the :py:class:`~engine.Context` class. The type
resolver function is expected to take a single argument, and that is the name of the symbol (as a Python string) whose
type needs to be resolved. The return type should be a member of the :py:class:`~types.DataType` enumeration.

.. code-block:: python

   # define a basic type resolver, that knows about the four attributes of a
   # comic book
   def type_resolver(name):
       if name == 'title':
           return rule_engine.DataType.STRING
       elif name == 'publisher':
           return rule_engine.DataType.STRING
       elif name == 'issue':
           return rule_engine.DataType.FLOAT
       elif name == 'released':
           return rule_engine.DataType.DATETIME
       # if the name is none of those, raise a SymbolResolutionError
       raise rule_engine.errors.SymbolResolutionError(name)

   context = rule_engine.Context(type_resolver=type_resolver)

:py:attr:`~.DataType.UNDEFINED` can be defined as the data type for a valid symbol without specifying explicit type
information. In this case, the rule object will know that it is a valid symbol, but will not validate any operations
that reference it.

In all cases, when a *type_resolver* is defined, the :py:class:`~engine.Rule` object will raise a
:py:class:`~errors.SymbolResolutionError` if a symbol is referenced in the rule that is not known to the
*type_resolver*.

.. code-block:: python

   # this is valid: issue is defined as a valid symbol
   rule = rule_engine.Rule('issue == 1', context=context)
   # => <Rule text='issue == 1' >

   # this is invalid: author is not defined as a valid symbol
   rule = rule_engine.Rule('author == "Stan Lee"', context=context)
   # => SymbolResolutionError: author

   # this is valid: no type information is defined (context is omitted)
   rule = rule_engine.Rule('author == "Stan Lee"')
   # => <Rule text='author == "Stan Lee"' >

.. _getting-started-object-data-types:

Object Data Types
"""""""""""""""""

.. versionadded:: 5.0.0

The :py:attr:`~.DataType.OBJECT` type defines a schema with named, typed attributes. This gives parse-time validation:
an unknown attribute in a rule will raise an error immediately, before the rule is ever applied to real data.

Continuing the comic book example, suppose the data is backed by Python objects instead of plain dictionaries:

.. code-block:: python

   import dataclasses
   import datetime
   import rule_engine

   @dataclasses.dataclass
   class Hero:
       name: str
       publisher: str
       first_appearance: datetime.date
       nemesis: 'Hero' = None  # self-referential

Define the corresponding ``OBJECT`` type and place it in the ``type_resolver``. Use
:py:attr:`~.DataType.OBJECT.self` as a shorthand for the self-referential ``nemesis`` attribute (or
:py:meth:`~.DataType.OBJECT.reference` by name for cross-type references):

.. code-block:: python

   HeroType = rule_engine.DataType.OBJECT('Hero', attributes={
       'name': rule_engine.DataType.STRING,
       'publisher': rule_engine.DataType.STRING,
       'first_appearance': rule_engine.DataType.DATETIME,
       'nemesis': rule_engine.DataType.OBJECT.self,
   })

   context = rule_engine.Context(type_resolver={
       'hero': HeroType,
       'Hero': HeroType,
   })

Now rules get attribute validation at parse time:

.. code-block:: python

   # valid rule - 'name' is in the schema
   rule = rule_engine.Rule('hero.name == "Batman"', context=context)

   # invalid rule - 'secret_identity' is not in the schema
   rule = rule_engine.Rule('hero.secret_identity == "Bruce Wayne"', context=context)
   # => ObjectAttributeError: unknown attribute: 'secret_identity'

Self-referential chains work automatically:

.. code-block:: python

   rule = rule_engine.Rule('hero.nemesis.name == "Joker"', context=context)

   batman = Hero('Batman', 'DC', datetime.date(1939, 5, 1))
   joker = Hero('Joker', 'DC', datetime.date(1940, 4, 25), nemesis=batman)
   batman.nemesis = joker

   rule.matches({'hero': batman})  # => True

For mutually recursive types (e.g. ``Hero`` and ``Sidekick``), place both types in the same ``type_resolver`` dict.
Cross-type references are resolved lazily at rule parse time - see the :ref:`OBJECT reference<data-types>` in the Data
Types page for a full example.

.. note::

   ``OBJECT`` attributes are accessed with dot syntax (``hero.name``). Item access (``hero["name"]``) is not supported
   and will raise a parse-time error. If your data is dictionary-shaped, consider using the ``accessor`` parameter to
   customize how values are fetched - see :py:attr:`~.DataType.OBJECT` for details.

.. _getting-started-compound-data-types:

Compound Data Types
"""""""""""""""""""
Compound data types such as the :py:attr:`~.DataType.ARRAY` and :py:attr:`~.DataType.MAPPING` types can optionally
specify member type information by calling their respective type. For example, an array of strings would be defined as
``DataType.ARRAY(DataType.STRING)`` while a mapping with string keys and float values would be defined as
``DataType.MAPPING(DataType.STRING, DataType.FLOAT)``. For more information, see the documentation for the
:py:attr:`~.DataType.ARRAY`, :py:attr:`~.DataType.MAPPING` functions.

Compound member types can only be a single data type. In some cases the data type can optionally be nullable which means
that the member value can be either the specified type or :py:attr:`~.DataType.NULL`. For example, a
:py:attr:`~.DataType.MAPPING` type whose values are all nullable strings may be defined, while a
:py:attr:`~.DataType.MAPPING` type with one value type of a :py:attr:`~.DataType.STRING` and another of a
:py:attr:`~.DataType.BOOLEAN` may not be defined. In this case, the key type may be defined while the value type is set
to :py:attr:`~.DataType.UNDEFINED` which is the default value.

Function Data Types
"""""""""""""""""""
Like compound types, functions can include type information by calling the respective type, in this case
:py:attr:`~.DataType.FUNCTION`. Functions only support positional arguments and not keyword arguments but positional
arguments can be defined as optional through the *minimum_arguments* option.

For example, the :ref:`builtin split<builtin-function-split>` can be called with as few as 1 arguments and as many as
3 arguments. The first argument is always required, so *minimum_arguments* is set to 1. This means the remaining 2
arguments are optional, however for the third argument to be defined in a function call, the second must also be
defined. For the split function, the first argument is the string to split, followed by the seperator string to split on
and finally the maximum number of times to split the string.

.. code-block:: python

   rule_engine.DataType.FUNCTION(
       # the name of the function is provided for error messages
       'split',
       # the return data type, in this case an array of strings
       return_type=rule_engine.DataType.ARRAY(rule_engine.DataType.STRING),
       # the data type of each of the three arguments
       argument_types=(
          rule_engine.DataType.STRING, # argument 1, the string to split
          rule_engine.DataType.STRING, # argument 2, the seperator to split on
          rule_engine.DataType.FLOAT   # argument 3, the maximum times to split the string
       ),
       # the minimum number of arguments, in this case the second two arguments are optional
       minimum_arguments=1
   )

If the return type, or argument types are not specified, then no type checking is preformed.

Defining Types From A Dictionary
""""""""""""""""""""""""""""""""
For convenience, the :py:func:`~engine.type_resolver_from_dict` function can be used to generate a *type_resolver*
function from a dictionary mapping symbol names to their respective :py:class:`~types.DataType`. Starting with version
:release:`2.1.0` if a :py:class:`dict` is passed as the *type_resolver*, the :py:func:`~engine.type_resolver_from_dict`
function will be used automatically.

.. code-block:: python

   context = rule_engine.Context(
       type_resolver=rule_engine.type_resolver_from_dict({
           # map symbol names to their data types
           'title':     rule_engine.DataType.STRING,
           'publisher': rule_engine.DataType.STRING,
           'issue':     rule_engine.DataType.FLOAT,
           'released':  rule_engine.DataType.DATETIME
       })
   )

.. _getting-started-types-from-dataclass:

Defining Types From A Dataclass
"""""""""""""""""""""""""""""""

.. versionadded:: 5.0.0

When the source data is modeled as a :py:func:`~dataclasses.dataclass`, the
:py:func:`~engine.type_resolver_from_dataclass` helper builds a *type_resolver* directly from the field annotations.
The dataclass's fields become the top-level resolvable symbols, and any nested dataclasses (including self- and
mutually-recursive references) are reachable through attribute access on the resolved ``OBJECT``.

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

   context = rule_engine.Context(
       resolver=rule_engine.resolve_attribute,
       type_resolver=rule_engine.type_resolver_from_dataclass(Hero),
   )

   rule = rule_engine.Rule('name == "Batman" and sidekick == "Robin"', context=context)
   batman = Hero('Batman', 'DC', datetime.datetime(1939, 5, 1), sidekick='Robin')
   rule.matches(batman)  # => True

:py:class:`~typing.Optional` annotations (and the PEP 604 ``T | None`` form) are unwrapped so the attribute carries the
underlying type and is marked nullable. Fields whose annotation is itself a dataclass become nested ``OBJECT`` types
automatically, and ``list[Other]`` / ``dict[str, Other]`` style containers are walked so nested dataclass schemas
inside compound types are also expanded. See :ref:`the OBJECT documentation<getting-started-object-data-types>` for
details on the resulting schema's behavior.

.. _getting-started-types-from-sqlalchemy:

Defining Types From A SQLAlchemy Model
""""""""""""""""""""""""""""""""""""""

.. versionadded:: 5.0.0

Projects that already use `SQLAlchemy <https://www.sqlalchemy.org/>`_ can feed a mapped class into
:py:func:`~engine.type_resolver_from_sqlalchemy` to obtain a type resolver without restating the schema.
SQLAlchemy is **not** a runtime dependency of Rule Engine; install it separately
(``pip install "sqlalchemy>=2.0"``) only if you intend to call this helper.

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

   context = rule_engine.Context(
       resolver=rule_engine.resolve_attribute,
       type_resolver=rule_engine.type_resolver_from_sqlalchemy(Hero),
   )

   rule = rule_engine.Rule('name == "Batman" and active', context=context)
   batman = Hero(id=1, name='Batman', alias='Bruce Wayne',
                 first_appearance=datetime.datetime(1939, 5, 1), active=True)
   rule.matches(batman)  # => True

Column nullability (``column.nullable``) is copied through, ``Mapped[T | None]`` is honored, and mapped
relationships expand into nested ``OBJECT`` schemas (with ``uselist`` collections wrapped in
:py:attr:`~rule_engine.types.DataType.ARRAY`). Self-references and cycles between mutually related classes
resolve at parse time because every reachable schema is registered by name on the resulting resolver. See the
:ref:`OBJECT documentation<getting-started-object-data-types>` for the full column-to-type mapping and limits.

.. _changing-builtin-symbols:

Changing Builtin Symbols
^^^^^^^^^^^^^^^^^^^^^^^^
To remove the default :ref:`builtin symbols<builtin-symbols>` that are provided, simply initialize a
:py:class:`~rule_engine.builtins.Builtins` instance with a *values* of an empty dictionary. This will remove all builtin
values, and the dictionary can optionally be populated with alternative values.

To add additional values, use the :py:class:`~rule_engine.builtins.Builtins.from_defaults` constructor, with a *values*
dictionary. In this case, *values* will optionally override any of the default settings, and keys which do not overlap
will be added in addition to the default builtin symbols.

.. code-block:: python

   class CustomBuiltinsContext(rule_engine.Context):
       def __init__(self, *args, **kwargs):
           # call the parent class's __init__ method first to set the
           # default_timezone attribute
           super(CustomBuiltinsContext, self).__init__(*args, **kwargs)
           self.builtins = rule_engine.builtins.Builtins.from_defaults(
               # expose the $version symbol
               {'version': rule_engine.__version__},
               # use the specified default timezone
               timezone=self.default_timezone
           )

Rule Inspection
---------------
There are a few techniques that can be used to inspect a rule object.

* :py:meth:`~engine.Rule.is_valid` -- This class method can be used to determine if a rule expression is valid. It will
  return ``False`` if for example there are any syntax errors.
* :py:attr:`~engine.Context.symbols` -- Rule objects have a :py:attr:`~engine.Rule.context` attribute, which contains
  the ``symbols`` attribute. This contains the symbol names which were identified within the rule expression.
* :py:meth:`~engine.Rule.to_graphviz` -- This method will create a Graphviz directed-graph of the Rule Engine Abstract
  Syntax Tree (AST) created by the rule expression. This can be helpful when debugging complex rules. This requires the
  Python ``graphviz`` package to be available.
