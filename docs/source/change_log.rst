Change Log
==========

This document contains notes on the major changes for each version of the Rule
Engine. In comparison to the git log, this list is curated by the development
team for note worthy changes.

Version 2.x.x
-------------

Version 2.0.0
^^^^^^^^^^^^^

*In Progress*

* Added proper support for attributes
* Added a change log
* Added additional information to the Graphviz output
* Added the new :py:class:`~rule_engine.ast.DataType.ARRAY` data type
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
