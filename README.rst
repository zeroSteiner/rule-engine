Rule Engine
===========
A lightweight, optionally typed expression language with a custom grammar for matching arbitrary Python objects.

Documentation is available at https://zeroSteiner.github.io/rule-engine/.

Rule Engine expressions are written in their own language, defined as strings in Python. Some features of this language
includes:

- Optional type hinting
- Matching strings with regular expressions
- Datetime datatypes
- Data attributes

Example
-------
The following example demonstrates the basic usage of defining a rule object and applying it to two dictionaries,
showing that one matches while the other does not. See `Getting Started`_ for more information.

.. code-block:: python

   import rule_engine
   # match a literal first name and applying a regex to the email
   rule = rule_engine.Rule(
       'first_name == "Luke" and email =~ ".*@rebels.org$"'
   ) # => <Rule text='first_name == "Luke" and email =~ ".*@rebels.org$"' >
   rule.matches({
       'first_name': 'Luke', 'last_name': 'Skywalker', 'email': 'luke@rebels.org'
   }) # => True
   rule.matches({
      'first_name': 'Darth', 'last_name': 'Vader', 'email': 'dvader@empire.net'
   }) # => False

The next example demonstrates the optional type system. A custom context is created that defines two symbols, one string
and one float. Because symbols are defined, an exception will be raised if an unknown symbol is specified or an invalid
operation is used. See `Type Hinting`_ for more information.

.. code-block:: python

   import rule_engine
   # define the custom context with two symbols
   context = rule_engine.Context(type_resolver=rule_engine.type_resolver_from_dict({
       'first_name': rule_engine.DataType.STRING,
       'age': rule_engine.DataType.FLOAT
   }))

   # receive an error when an unknown symbol is used
   rule = rule_engine.Rule('last_name == "Vader"', context=context)
   # => SymbolResolutionError: last_name

   # receive an error when an invalid operation is used
   rule = rule_engine.Rule('first_name + 1', context=context)
   # => EvaluationError: data type mismatch

Credits
-------
* Spencer McIntyre - zeroSteiner (`@zeroSteiner <https://twitter.com/zeroSteiner>`_)

.. _Getting Started: https://zerosteiner.github.io/rule-engine/getting_started.html
.. _Type Hinting: https://zerosteiner.github.io/rule-engine/getting_started.html#type-hinting
