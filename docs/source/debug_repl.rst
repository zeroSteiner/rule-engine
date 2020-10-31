.. _debug-repl:

Debug REPL
==========
Since version :release:`2.4.0`, the Rule Engine package includes a module which provides a Read Eval Print Loop (REPL)
for debugging and testing purposes. This module can be executed using ``python -m rule_engine.debug_repl``. Once
started, the REPL loop can be used to evaluate rule expressions and view the results.

CLI Arguments
-------------

The module when executed from the command line has the following options available.

.. program:: debug_repl

.. option:: --edit-console

   Start an interactive Python console that allows the user to setup the environment for the rule evaluation.

.. option:: --edit-file <path>

   Run the specified file containing Python source code, allowing it to setup the environment for the rule evaluation.

Configuration
-------------
When configured through either the ``--edit-console`` or ``--edit-file`` options, the ``context`` symbol may be
customized using a user-defined :py:class:`~rule_engine.engine.Context` instance. Additionally, the object to evaluate
can be configured through the ``thing`` symbol.

Example Usage
-------------
The following example demonstrates using the Debug REPL with a *thing* (in this case a comic book) defined through the
interactive console.

.. code-block:: text

    python -m rule_engine.debug_repl --edit-console
    edit the 'context' and 'thing' objects as necessary
    >>> thing = dict(title='Batman', publisher='DC', issue=1)
    >>> exit()
    exiting the edit console...
    rule > title == 'Superman'
    result:
    False
    rule > issue < 5
    result:
    True
    rule >
