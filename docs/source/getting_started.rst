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

Advanced Usage
--------------
The Rule Engine has a number of advanced features that contribute to its flexibility. In most use cases they are
unnecessary.

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
type needs to be resolved. The return type should be a member of the :py:class:`~ast.DataType` enumeration.

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
       return_type=ast.DataType.ARRAY(ast.DataType.STRING),
       # the data type of each of the three arguments
       argument_types=(
          ast.DataType.STRING, # argument 1, the string to split
          ast.DataType.STRING, # argument 2, the seperator to split on
          ast.DataType.FLOAT   # argument 3, the maximum times to split the string
       ),
       # the minimum number of arguments, in this case the second two arguments are optional
       minimum_arguments=1
   )

If the return type, or argument types are not specified, then no type checking is preformed.

Defining Types From A Dictionary
""""""""""""""""""""""""""""""""
For convenience, the :py:func:`~engine.type_resolver_from_dict` function can be used to generate a *type_resolver*
function from a dictionary mapping symbol names to their respective :py:class:`~ast.DataType`. Starting with version
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
