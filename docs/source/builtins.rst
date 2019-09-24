.. py:currentmodule:: rule_engine

Builtin Symbols
===============
The following symbols are provided by default using the
:py:meth:`~engine.Builtins.from_defaults` method. These symbols can be accessed
through the ``$`` prefix. The default values can be overridden by defining a
custom subclass of :py:class:`~engine.Context` and setting the
:py:attr:`~engine.Context.builtins`.

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
