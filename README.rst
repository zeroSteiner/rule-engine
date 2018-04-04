Rule Engine
===========
This project provides a library for creating general purpose "Rule" objects from
a logical expression which can then be applied to arbitrary objects to evaluate
whether or not they match.

Documentation is available at https://zeroSteiner.github.io/rule-engine/.

Example
-------

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

Credits
-------
* Spencer McIntyre - zeroSteiner (`@zeroSteiner <https://twitter.com/zeroSteiner>`_)
