.. py:currentmodule:: rule_engine

Getting Started
===============
The Rule Engine is meant to allow developers to filter arbitrary Python objects
with a "rule" specified either by them or by an end user. The "rules" that the
Rule Engine uses are Python string expressions in a custom language. The syntax
that Rule Engine uses is similar to Python by borrows some features from Ruby.
The rules are a custom language and no Python ``exec`` or ``eval`` operations
are used, allowing developers to safely and security evaluate rules provided by
potentially untrusted sources.

Basic Usage
-----------
#. The developer needs to identify data that they would like to be filtered.
   This would be some kind of object with a set of variable attributes. The
   rest of the usage example will assume that these objects are comic books.

   * Comic books have various attributes that could be useful for filtering
     including:

      +-----------+-----------------------+-----------------------------------+
      | Attribute | Python Type           | Rule Engine Type                  |
      +-----------+-----------------------+-----------------------------------+
      | title     | ``str``               | :py:attr:`~ast.DataType.STRING`   |
      +-----------+-----------------------+-----------------------------------+
      | publisher | ``str``               | :py:attr:`~ast.DataType.STRING`   |
      +-----------+-----------------------+-----------------------------------+
      | issue     | ``int``               | :py:attr:`~ast.DataType.FLOAT`    |
      +-----------+-----------------------+-----------------------------------+
      | released  | ``datetime.date``     | :py:attr:`~ast.DataType.DATETIME` |
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

#. Now the developer needs to create a rule object to match the target objects.
   The attributes of the objects will automatically become valid symbols for the
   rule expression. Creating a rule object is done by initializing an instance
   of the :py:class:`~engine.Rule` class which requires one argument, and that
   is the string expression (in Rule Engine syntax) of the rule.

   * In the case of the comic book collection, these symbols would be:
     ``title``, ``publisher``, ``issue``, and ``released``. Notice that these
     attribute names are also valid symbol names, i.e. they start with a letter
     and contain note whitespace or punctuation. Just like in Python, Rule
     Engine symbols must follow these rules. For example, ``released`` is a
     valid symbol while ``Released Date`` is not (because of the space).

   * An example rule for the comic book collection might look like:

      .. code-block:: python

         rule = rule_engine.Rule(
           # match books published by DC
           'publisher == "DC"'
         )

#. Once the rule object has been defined, it can be applied to target object(s).
   Two primary methods are available for applying the rule to the target objects.
   Those methods are:

   * :py:meth:`~engine.Rule.matches` -- This method will determine whether the
     rule matches a single target object, returning ``True`` or ``False``.
   * :py:meth:`~engine.Rule.filter` -- This method will filter an iterable of
     target objects, yielding ones for which the rule matches.

   * Applying the rule to the comic book collection using each of the two
     methods might look like:

      .. code-block:: python

         # check if the first object matches
         rule.matches(comics[0]) # => True

         # filter the iterable "comics" and return matching objects
         rule.filter(comics) # => <generator object Rule.filter at 0x7f2bdafbe650>

Rule Inspection
---------------
There are a few techniques that can be used to inspect a rule object.

* :py:meth:`~engine.Rule.is_valid` -- This class method can be used to determine
  if a rule expression is valid. It will return ``False`` if for example there
  are any syntax errors.
* :py:attr:`~engine.Context.symbols` -- Rule objects have a
  :py:attr:`~engine.Rule.context` attribute, which contains the ``symbols``
  attribute. This contains the symbol names which were identified within the
  rule expression.
* :py:meth:`~engine.Rule.to_graphviz` -- This method will create a Graphviz
  directed-graph of the Rule Engine Abstract Syntax Tree (AST) created by the
  rule expression. This can be helpful when debugging complex rules. This
  requires the Python ``graphviz`` package to be available.