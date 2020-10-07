Change Log
==========

This document contains notes on the major changes for each version of the Rule Engine. In comparison to the git log,
this list is curated by the development team for note worthy changes.

Version 2.x.x
-------------

Version 2.3.0
^^^^^^^^^^^^^

*In progress*

* Added support for arithmetic comparisons for all currently supported data types
* Added support for proper type hinting of builtin symbols
* Added the ``$re_groups`` builtin symbol for extracting groups from a regular expression match

Version 2.2.0
^^^^^^^^^^^^^

Released :release:`2.1.0` on September 9th, 2020

* Added script entries to the Pipfile for development
* Added support for slices on sequence data types

Version 2.1.0
^^^^^^^^^^^^^

Released :release:`2.1.0` on August 3rd, 2020

* Added coverage reporting to Travis-CI
* Changed :py:class:`~rule_engine.ast.DataType` from an enum to a custom class
* Improvements for the :py:class:`~rule_engine.ast.DataType.ARRAY` data type

    * Added `get[item]` support for arrays, allowing items to be retrieved by index
    * Added ability for specifying the member type and optionally null

Version 2.0.0
^^^^^^^^^^^^^

Released :release:`2.0.0` on October 2nd, 2019

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
