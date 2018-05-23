Rule Engine Documentation
=========================
This project provides a library for creating general purpose "Rule" objects from
a logical expression which can then be applied to arbitrary objects to evaluate
whether or not they match.

The source code is available on the `GitHub homepage`_.

Symbol Resolution
-----------------

Symbols / variables in rules can be resolved from objects using an arbitrary
function. Two are builtin, one for resolving symbols
:py:func:`as keys<rule_engine.engine.resolve_item>` on objects (such as
dictionaries) and one for resolving symbols
:py:func:`as attributes<rule_engine.engine.resolve_attribute>` on objects.

Type Hinting
------------

Symbol type information can be provided to the
:py:class:`~rule_engine.engine.Engine` through a
:py:class:`~rule_engine.engine.Context` instance and will be used for
compatibility testing. With type information, the engine will raise an
:py:class:`~rule_engine.errors.EvaluationError` when an incompatible operation
is detected such a regex match (``=~``) using an integer on either side. This
makes it easier to detect errors in a rule's syntax prior to it being applied to
an object.

Alternatively, a function can be specified that simply returns
:py:attr:`~rule_engine.ast.DataType.UNDEFINED` for valid symbols. In both cases
the engine will raise a :py:class:`~rule_engine.errors.SymbolResolutionError`
when an invalid symbol is specified in a rule.

Usage Example
-------------

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

See the `examples`_ folder for more.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   syntax.rst
   rule_engine/index.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _examples: https://github.com/zeroSteiner/rule-engine/tree/master/examples
.. _GitHub homepage: https://github.com/zeroSteiner/rule-engine
