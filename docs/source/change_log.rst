Change Log
==========

This document contains notes on the major changes for each version of the Rule Engine. In comparison to the git log,
this list is curated by the development team for note worthy changes.

Version 4.x.x
-------------

Version 4.5.0
^^^^^^^^^^^^^

Released :release:`4.5.0` on June 19th, 2024

* :py:class:`~rule_engine.errors.StringSyntaxError` is now raised for invalid string literals
* :py:class:`~rule_engine.errors.FunctionCallError` is now raised when a typed function returns an incompatible value
* Added the new :py:class:`~rule_engine.types.DataType.BYTES` data type
* Added some new data attributes

    * Added ``starts_with`` and ``ends_with`` to :py:class:`~rule_engine.types.DataType.ARRAY`, and
      :py:class:`~rule_engine.types.DataType.STRING`

Version 4.4.0
^^^^^^^^^^^^^

Released :release:`4.4.0` on April 5th, 2024

* Added the ``$range`` builtin function
* Added the ``rule_engine.parser.utilities`` module with a few functions and documentation

Version 4.3.0
^^^^^^^^^^^^^

Released :release:`4.3.0` on January 15th, 2024

* Added the ``is_nan`` attribute for ``FLOAT`` values

Version 4.2.0
^^^^^^^^^^^^^

Released :release:`4.2.0` on December 11th, 2023

* Added attributes for coercion of types to themselves, e.g. ``to_str`` for ``STRING`` values

Version 4.1.0
^^^^^^^^^^^^^

Released :release:`4.1.0` on August 3rd, 2023

* Added the ``$abs`` builtin function
* Added support to :py:class:`~rule_engine.types.DataType.from_type` to handle Python's type hints

Version 4.0.0
^^^^^^^^^^^^^

Released :release:`4.0.0` on July 15th, 2023

* **Breaking:** Changed ``STRING.to_ary`` to return an array of characters instead of splitting the string

    * Use the new builtin ``$split`` function to split a string on whitespace into an array of words

* **Breaking:** Changed :py:class:`~rule_engine.engine.Context` to use keyword-only arguments
* **Breaking:** Dropped support for Python versions 3.4 and 3.5
* **Breaking:** Invalid floating point literals now raise :py:exc:`~.errors.FloatSyntaxError` instead of
  :py:exc:`~.errors.RuleSyntaxError`
* **Breaking:** Moved ``rule_engine.engine.Builtins`` to :py:class:`rule_engine.builtins.Builtins`
* Added the new :py:class:`~rule_engine.types.DataType.FUNCTION` data type

Version 3.x.x
-------------

Version 3.6.0
^^^^^^^^^^^^^

Released :release:`3.6.0` on June 16th, 2023

* Removed testing for Python versions 3.4 and 3.5 on GitHub Actions
* Add regex error details to the debug REPL
* Add support for Python-style comments

Version 3.5.0
^^^^^^^^^^^^^

Released :release:`3.5.0` on July 16th, 2022

* Added the new :py:class:`~rule_engine.types.DataType.TIMEDELTA` data type

Version 3.4.0
^^^^^^^^^^^^^

Released :release:`3.4.0` on March 19th, 2022

* Add support for string concatenation via the ``+`` operator

Version 3.3.0
^^^^^^^^^^^^^

Released :release:`3.3.0` on July 20th, 2021

* Added ``to_epoch`` to :py:class:`~rule_engine.types.DataType.DATETIME`

Version 3.2.0
^^^^^^^^^^^^^

Released :release:`3.2.0` on April 3rd, 2021

* Refactored the :py:mod:`~rule_engine.ast` module to move the :py:class:`~rule_engine.types.DataType` class into a new,
  dedicated :py:mod:`~rule_engine.types` module.
* Added the new :py:class:`~rule_engine.ast.ComprehensionExpression`
* Added suggestions to :py:class:`~rule_engine.errors.AttributeResolutionError` and
  :py:class:`~rule_engine.errors.SymbolResolutionError`

Version 3.1.0
^^^^^^^^^^^^^

Released :release:`3.1.0` on March 15th, 2021

* Added the new :py:class:`~rule_engine.types.DataType.SET` data type

Version 3.0.0
^^^^^^^^^^^^^

Released :release:`3.0.0` on March 1st, 2021

* Switched the ``FLOAT`` datatype to use Python's :py:class:`~decimal.Decimal` from :py:class:`float` internally
* Reserved the ``if``, ``elif``, ``else``, ``for`` and ``while`` keywords for future use, they can no longer be used as
  symbol names
* Added some new data attributes

    * Added ``ceiling``, ``floor`` and ``to_str`` to :py:class:`~rule_engine.types.DataType.FLOAT`

Version 2.x.x
-------------

Version 2.4.0
^^^^^^^^^^^^^

Released :release:`2.4.0` on November 7th, 2020

* Added the :ref:`debug-repl` utility
* Added the safe navigation version of the attribute, item and slice operators
* Added the new :py:class:`~rule_engine.types.DataType.MAPPING` data type
* Switched from Travis-CI to GitHub Actions for continuous integration
* Added support for iterables to have multiple member types

Version 2.3.0
^^^^^^^^^^^^^

Released :release:`2.3.0` on October 11th, 2020

* Added support for arithmetic comparisons for all currently supported data types
* Added support for proper type hinting of builtin symbols
* Added the ``$re_groups`` builtin symbol for extracting groups from a regular expression match
* Added some new data attributes

    * Added ``to_ary`` to :py:class:`~rule_engine.types.DataType.STRING`
    * Added ``to_int`` and ``to_flt`` to :py:class:`~rule_engine.types.DataType.STRING`

Version 2.2.0
^^^^^^^^^^^^^

Released :release:`2.2.0` on September 9th, 2020

* Added script entries to the Pipfile for development
* Added support for slices on sequence data types

Version 2.1.0
^^^^^^^^^^^^^

Released :release:`2.1.0` on August 3rd, 2020

* Added coverage reporting to Travis-CI
* Changed :py:class:`~rule_engine.types.DataType`. from an enum to a custom class
* Improvements for the :py:class:`~rule_engine.types.DataType.ARRAY` data type

    * Added ``get[item]`` support for arrays, allowing items to be retrieved by index
    * Added ability for specifying the member type and optionally null

Version 2.0.0
^^^^^^^^^^^^^

Released :release:`2.0.0` on October 2nd, 2019

* Added proper support for attributes
* Added a change log
* Added additional information to the Graphviz output
* Added the new :py:class:`~rule_engine.types.DataType.ARRAY` data type
* Started using Travis-CI

    * Added automatic unit testing using Travis-CI
    * Added automatic deployment of documentation using Travis-CI

* Removed the resolver conversion functions

    * Removed ``to_recursive_resolver`` in favor of attributes
    * Removed ``to_default_resolver`` in favor of the *default_value* kwarg to
      :py:meth:`~rule_engine.engine.Context.__init__`

Version 1.x.x
-------------

Version 1.1.0
^^^^^^^^^^^^^

Released :release:`1.1.0` on March 27th, 2019

* Added the :py:func:`~rule_engine.engine.to_default_dict` function
* Added the :py:func:`~rule_engine.engine.to_recursive_resolver` function

Version 1.0.0
^^^^^^^^^^^^^

Released :release:`1.0.0` on December 15th, 2018

* First major release
