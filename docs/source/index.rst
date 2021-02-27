Rule Engine Documentation
=========================
This project provides a library for creating general purpose "Rule" objects from a logical expression which can then be
applied to arbitrary objects to evaluate whether or not they match.

Documentation is available at https://zeroSteiner.github.io/rule-engine/.

Rule Engine expressions are written in their own language, defined as strings in Python. Some features of this language
includes:

* Optional type hinting
* Matching strings with regular expressions
* Datetime datatypes
* Data attributes

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

   getting_started.rst
   syntax.rst
   types.rst
   attributes.rst
   rule_engine/index.rst
   debug_repl.rst
   change_log.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _examples: https://github.com/zeroSteiner/rule-engine/tree/master/examples
.. _GitHub homepage: https://github.com/zeroSteiner/rule-engine
