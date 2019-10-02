.. py:currentmodule:: rule_engine.engine

Builtin Symbols
===============
The following symbols are provided by default using the
:py:meth:`~Builtins.from_defaults` method. These symbols can be accessed through
the ``$`` prefix, e.g. ``$pi``. The default values can be overridden by defining
a custom subclass of :py:class:`~Context` and setting the
:py:attr:`~Context.builtins` attribute.

+-------+-----------------------------------+----------------------------------------------+
| Name  | Data Type                         | Value Description                            |
+-------+-----------------------------------+----------------------------------------------+
| **Math related**                                                                         |
+-------+-----------------------------------+----------------------------------------------+
| e     | :py:attr:`~ast.DataType.FLOAT`    | The mathematical constant *e* (2.71828...).  |
+-------+-----------------------------------+----------------------------------------------+
| pi    | :py:attr:`~ast.DataType.FLOAT`    | The mathematical constant *pi* (3.14159...). |
+-------+-----------------------------------+----------------------------------------------+
| **Timestamp related**                                                                    |
+-------+-----------------------------------+----------------------------------------------+
| now   | :py:attr:`~ast.DataType.DATETIME` | The current timestamp (including time)       |
|       |                                   | using the default timezone from              |
|       |                                   | :py:attr:`~engine.Context.default_timestamp` |
+-------+-----------------------------------+----------------------------------------------+
| today | :py:attr:`~ast.DataType.DATETIME` | The current timestamp, (excluding time)      |
|       |                                   | using the default timezone from              |
|       |                                   | :py:attr:`~engine.Context.default_timestamp` |
+-------+-----------------------------------+----------------------------------------------+

Defining Custom Values
----------------------
To remove the default builtins described above, simply initialize a
:py:class:`~Builtins` instance with a *values* of an empty dictionary. This will
remove all builtin values, and the dictionary can optionally be populated with
alternative values.

To add additional values, use the :py:class:`~Builtins.from_defaults`
constructor, with a *values* dictionary. In this case, *values* will optionally
override any of the default settings, and keys which do not overlap will be
added in addition to the default builtin symbols.

.. code-block:: python

   class CustomBuiltinsContext(rule_engine.Context):
       def __init__(self, *args, **kwargs):
           # call the parent class's __init__ method first to set the
           # default_timezone attribute
           super(CustomBuiltinsContext, self).__init__(*args, **kwargs)
           self.builtins = rule_engine.engine.Builtins.from_defaults(
               # expose the $version symbol
               {'version': rule_engine.__version__},
               # use the specified default timezone
               timezone=self.default_timezone
           )
