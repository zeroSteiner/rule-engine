#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/types.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import collections
import collections.abc
import datetime
import decimal
import math

from . import errors

__all__ = (
	'DataType',
	'NoneType',
	'coerce_value',
	'is_integer_number',
	'is_natural_number',
	'is_numeric',
	'is_real_number',
	'iterable_member_value_type'
)

_PYTHON_FUNCTION_TYPE = type(lambda: None)
NoneType = type(None)

def _to_decimal(value):
	if isinstance(value, decimal.Decimal):
		return value
	return decimal.Decimal(repr(value))

def coerce_value(value, verify_type=True):
	"""
	Take a native Python *value* and convert it to a value of a data type which can be represented by a Rule Engine
	:py:class:`~.DataType`. This function is useful for converting native Python values at the engine boundaries such as
	when resolving a symbol from an object external to the engine.

	.. versionadded:: 2.0.0

	:param value: The value to convert.
	:param bool verify_type: Whether or not to verify the converted value's type.
	:return: The converted value.
	"""
	# ARRAY
	if isinstance(value, (list, range, tuple)):
		value = tuple(coerce_value(v, verify_type=verify_type) for v in value)
	# DATETIME
	elif isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
		value = datetime.datetime(value.year, value.month, value.day)
	# FLOAT
	elif isinstance(value, (float, int)) and not isinstance(value, bool):
		value = _to_decimal(value)
	# MAPPING
	elif isinstance(value, (dict, collections.OrderedDict)):
		value = collections.OrderedDict(
			(coerce_value(k, verify_type=verify_type), coerce_value(v, verify_type=verify_type)) for k, v in value.items()
		)
	if verify_type:
		DataType.from_value(value)  # use this to raise a TypeError, if the type is incompatible
	return value

def is_integer_number(value):
	"""
	Check whether *value* is an integer number (i.e. a whole, number). This can, for example, be used to check if a
	floating point number such as ``3.0`` can safely be converted to an integer without loss of information.

	.. versionadded:: 2.1.0

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is an integer number.
	:rtype: bool
	"""
	if not is_real_number(value):
		return False
	if math.floor(value) != value:
		return False
	return True

def is_natural_number(value):
	"""
	Check whether *value* is a natural number (i.e. a whole, non-negative number). This can, for example, be used to
	check if a floating point number such as ``3.0`` can safely be converted to an integer without loss of information.

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is a natural number.
	:rtype: bool
	"""
	if not is_integer_number(value):
		return False
	if value < 0:
		return False
	return True

def is_real_number(value):
	"""
	Check whether *value* is a real number (i.e. capable of being represented as a floating point value without loss of
	information as well as being finite). Despite being able to be represented as a float, ``NaN`` is not considered a
	real number for the purposes of this function.

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is a natural number.
	:rtype: bool
	"""
	if not is_numeric(value):
		return False
	if not math.isfinite(value):
		return False
	return True

def is_numeric(value):
	"""
	Check whether *value* is a numeric value (i.e. capable of being represented as a floating point value without loss
	of information).

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is numeric.
	:rtype: bool
	"""
	if not isinstance(value, (decimal.Decimal, float, int)):
		return False
	if isinstance(value, bool):
		return False
	return True

def iterable_member_value_type(python_value):
	"""
	Take a native *python_value* and return the corresponding data type of each of its members if the types are either
	the same or NULL. NULL is considered a special case to allow nullable-values. This by extension means that an
	iterable may not be defined as only capable of containing NULL values.

	:return: The data type of the sequence members. This will never be NULL, because that is considered a special case.
		It will either be UNSPECIFIED or one of the other types.
	"""
	subvalue_types = set()
	for subvalue in python_value:
		if DataType.is_definition(subvalue):
			subvalue_type = subvalue
		else:
			subvalue_type = DataType.from_value(subvalue)
		subvalue_types.add(subvalue_type)
	if DataType.NULL in subvalue_types:
		# treat NULL as a special case, allowing typed arrays to be a specified type *or* NULL
		# this however makes it impossible to define an array with a type of NULL
		subvalue_types.remove(DataType.NULL)
	if len(subvalue_types) == 1:
		subvalue_type = subvalue_types.pop()
	else:
		subvalue_type = DataType.UNDEFINED
	return subvalue_type

class _DataTypeDef(object):
	__slots__ = ('name', 'python_type', 'is_scalar', 'iterable_type')
	def __init__(self, name, python_type):
		self.name = name
		self.python_type = python_type
		self.is_scalar = True
		if '__call__' in dir(self) and self.__call__.__doc__:
			# patch the call docs into the top-level class for Sphinx
			self.__class__.__doc__ = self.__call__.__doc__

	@property
	def is_iterable(self):
		return getattr(self, 'iterable_type', None) is not None

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False
		return self.name == other.name

	def __hash__(self):
		return hash((self.python_type, self.is_scalar))

	def __repr__(self):
		return "<{} name={} python_type={} >".format(self.__class__.__name__, self.name,  self.python_type.__name__)

	@property
	def is_compound(self):
		return not self.is_scalar

class _UndefinedDataTypeDef(_DataTypeDef):
	def __repr__(self):
		return 'UNDEFINED'

_DATA_TYPE_UNDEFINED = _UndefinedDataTypeDef('UNDEFINED', errors.UNDEFINED)

class _CollectionDataTypeDef(_DataTypeDef):
	__slots__ = ('value_type', 'value_type_nullable')
	def __init__(self, name, python_type, value_type=_DATA_TYPE_UNDEFINED, value_type_nullable=True):
		# check these three classes individually instead of using Collection which isn't available before Python v3.6
		if not issubclass(python_type, collections.abc.Container):
			raise TypeError('the specified python_type is not a container')
		if not issubclass(python_type, collections.abc.Iterable):
			raise TypeError('the specified python_type is not an iterable')
		if not issubclass(python_type, collections.abc.Sized):
			raise TypeError('the specified python_type is not a sized')
		super(_CollectionDataTypeDef, self).__init__(name, python_type)
		self.is_scalar = False
		self.value_type = value_type
		self.value_type_nullable = value_type_nullable

	@property
	def iterable_type(self):
		return self.value_type

	def __call__(self, value_type, value_type_nullable=True):
		"""
		:param value_type: The type of the members.
		:param bool value_type_nullable: Whether or not members are allowed to be :py:attr:`.NULL`.
		"""
		return self.__class__(
			self.name,
			self.python_type,
			value_type=value_type,
			value_type_nullable=value_type_nullable
		)

	def __repr__(self):
		return "<{} name={} python_type={} value_type={} >".format(
			self.__class__.__name__,
			self.name,
			self.python_type.__name__,
			self.value_type.name
		)

	def __eq__(self, other):
		if not super().__eq__(other):
			return False
		return all((
			self.value_type == other.value_type,
			self.value_type_nullable == other.value_type_nullable
		))

	def __hash__(self):
		return hash((self.python_type, self.is_scalar, hash((self.value_type, self.value_type_nullable))))

class _ArrayDataTypeDef(_CollectionDataTypeDef):
	pass

class _SetDataTypeDef(_CollectionDataTypeDef):
	pass

class _MappingDataTypeDef(_DataTypeDef):
	__slots__ = ('key_type', 'value_type', 'value_type_nullable')
	def __init__(self, name, python_type, key_type=_DATA_TYPE_UNDEFINED, value_type=_DATA_TYPE_UNDEFINED, value_type_nullable=True):
		if not issubclass(python_type, collections.abc.Mapping):
			raise TypeError('the specified python_type is not a mapping')
		super(_MappingDataTypeDef, self).__init__(name, python_type)
		self.is_scalar = False
		# ARRAY is the only compound data type that can be used as a mapping key, this is because ARRAY's are backed by
		# Python tuple's while SET and MAPPING objects are set and dict instances, respectively which are not hashable.
		if key_type.is_compound and not isinstance(key_type, DataType.ARRAY.__class__):
			raise errors.EngineError("the {} data type may not be used for mapping keys".format(key_type.name))
		self.key_type = key_type
		self.value_type = value_type
		self.value_type_nullable = value_type_nullable

	@property
	def iterable_type(self):
		return self.key_type

	def __call__(self, key_type, value_type=_DATA_TYPE_UNDEFINED, value_type_nullable=True):
		"""
		:param key_type: The type of the mapping keys.
		:param value_type: The type of the mapping values.
		:param bool value_type_nullable: Whether or not mapping values are allowed to be :py:attr:`.NULL`.
		"""
		return self.__class__(
			self.name,
			self.python_type,
			key_type=key_type,
			value_type=value_type,
			value_type_nullable=value_type_nullable
		)

	def __repr__(self):
		return "<{} name={} python_type={} key_type={} value_type={} >".format(
			self.__class__.__name__,
			self.name,
			self.python_type.__name__,
			self.key_type.name,
			self.value_type.name
		)

	def __eq__(self, other):
		if not super().__eq__(other):
			return False
		return all((
			self.key_type == other.key_type,
			self.value_type == other.value_type,
			self.value_type_nullable == other.value_type_nullable
		))

	def __hash__(self):
		return hash((self.python_type, self.is_scalar, hash((self.key_type, self.value_type, self.value_type_nullable))))

class _FunctionDataTypeDef(_DataTypeDef):
	__slots__ = ('value_name', 'return_type', 'argument_types', 'minimum_arguments')
	def __init__(self, name, python_type, value_name=None, return_type=_DATA_TYPE_UNDEFINED, argument_types=_DATA_TYPE_UNDEFINED, minimum_arguments=None):
		super(_FunctionDataTypeDef, self).__init__(name, python_type)
		self.value_name = value_name
		self.return_type = return_type
		if argument_types is _DATA_TYPE_UNDEFINED:
			if minimum_arguments is None:
				minimum_arguments = _DATA_TYPE_UNDEFINED
		else:
			if not isinstance(argument_types, collections.abc.Sequence):
				raise TypeError('argument_types must be a sequence (list or tuple)')
			if minimum_arguments is None:
				# if arguments are specified, assume that they're all required by default
				minimum_arguments = len(argument_types)
			if len(argument_types) < minimum_arguments:
				raise ValueError('minimum_arguments can not be greater than the length of argument_types')
		self.argument_types = argument_types
		self.minimum_arguments = minimum_arguments

	def __call__(self, name, return_type=_DATA_TYPE_UNDEFINED, argument_types=_DATA_TYPE_UNDEFINED, minimum_arguments=None):
		"""
		.. versionadded:: 4.0.0

		:param str name: The name of the function, e.g. "split".
		:param return_type: The data type of the functions return value.
		:param tuple argument_types: The data types of the functions arguments.
		:param int minimum_arguments: The minimum number of arguments the function requires.

		If *argument_types* is specified and *minimum_arguments* is not, then *minimum_arguments* will default to the length
		of *argument_types* effectively meaning that every defined argument is required. If
		"""
		return self.__class__(
			self.name,
			self.python_type,
			value_name=name,
			return_type=return_type,
			argument_types=argument_types,
			minimum_arguments=minimum_arguments
		)
	def __repr__(self):
		return "<{} name={} python_type={} return_type={} >".format(
			self.__class__.__name__,
			self.name,
			self.python_type.__name__,
			self.return_type.name
		)

	def __eq__(self, other):
		if not super().__eq__(other):
			return False
		return all((
			self.return_type == other.return_type,
			self.argument_types == other.argument_types,
			self.minimum_arguments == other.minimum_arguments
		))

	def __hash__(self):
		return hash((self.python_type, self.is_scalar, hash((self.return_type, self.argument_types, self.minimum_arguments))))

class DataTypeMeta(type):
	def __new__(metacls, cls, bases, classdict):
		data_type = super().__new__(metacls, cls, bases, classdict)
		members = []
		for key, value in classdict.items():
			if not key.upper() == key:
				continue
			if not isinstance(value, (_DataTypeDef, staticmethod)):
				continue
			members.append(key)
		data_type._members_ = tuple(members)
		return data_type

	def __contains__(self, item):
		return item in self._members_

	def __getitem__(cls, item):
		if item not in cls._members_:
			raise KeyError(item)
		return getattr(cls, item)

	def __iter__(cls):
		yield from cls._members_

	def __len__(cls):
		return len(cls._members_)

class DataType(metaclass=DataTypeMeta):
	"""
	A collection of constants representing the different supported data types. There are three ways to compare data
	types. All three are effectively the same when dealing with scalars.

	Equality checking
	  .. code-block::

	    dt == DataType.TYPE

	  This is the most explicit form of testing and when dealing with compound data types, it recursively checks that
	  all of the member types are also equal.

	Class checking
	  .. code-block::

	    isinstance(dt, DataType.TYPE.__class__)

	  This checks that the data types are the same but when dealing with compound data types, the member types are
	  ignored.

	Compatibility checking
	  .. code-block::

	    DataType.is_compatible(dt, DataType.TYPE)

	  This checks that the types are compatible without any kind of conversion. When dealing with compound data types,
	  this ensures that the member types are either the same or :py:attr:`~.UNDEFINED`.
	"""
	ARRAY = staticmethod(_ArrayDataTypeDef('ARRAY', tuple))
	BYTES = _DataTypeDef('BYTES', bytes)
	BOOLEAN = _DataTypeDef('BOOLEAN', bool)
	DATETIME = _DataTypeDef('DATETIME', datetime.datetime)
	FLOAT = _DataTypeDef('FLOAT', decimal.Decimal)
	FUNCTION = staticmethod(_FunctionDataTypeDef('FUNCTION', _PYTHON_FUNCTION_TYPE))
	MAPPING = staticmethod(_MappingDataTypeDef('MAPPING', dict))
	NULL = _DataTypeDef('NULL', NoneType)
	SET = staticmethod(_SetDataTypeDef('SET', set))
	STRING = _DataTypeDef('STRING', str)
	TIMEDELTA = _DataTypeDef('TIMEDELTA', datetime.timedelta)
	UNDEFINED = _DATA_TYPE_UNDEFINED
	"""
	Undefined values. This constant can be used to indicate that a particular symbol is valid, but it's data type is
	currently unknown.
	"""
	@classmethod
	def from_name(cls, name):
		"""
		Get the data type from its name.

		.. versionadded:: 2.0.0

		:param str name: The name of the data type to retrieve.
		:return: One of the constants.
		"""
		if not isinstance(name, str):
			raise TypeError('from_name argument 1 must be str, not ' + type(name).__name__)
		dt = getattr(cls, name, None)
		if not isinstance(dt, _DataTypeDef):
			raise ValueError("can not map name {0!r} to a compatible data type".format(name))
		return dt

	@classmethod
	def from_type(cls, python_type):
		"""
		Get the supported data type constant for the specified Python type/type hint. If the type or typehint can not be
		mapped to a supported data type, then a :py:exc:`ValueError` exception will be raised. This function will not
		return :py:attr:`.UNDEFINED`.

		:param type python_type: The native Python type or type hint to retrieve the corresponding type constant for.
		:return: One of the constants.

		.. versionchanged:: 4.1.0
			Added support for typehints.
		"""
		if not (isinstance(python_type, type) or hasattr(python_type, '__origin__')):
			raise TypeError('from_type argument 1 must be a type or a type hint, not ' + type(python_type).__name__)
		if python_type in (list, range, tuple):
			return cls.ARRAY
		elif python_type is bool:
			return cls.BOOLEAN
		elif python_type is bytes:
			return cls.BYTES
		elif python_type is datetime.date or python_type is datetime.datetime:
			return cls.DATETIME
		elif python_type is datetime.timedelta:
			return cls.TIMEDELTA
		elif python_type in (decimal.Decimal, float, int):
			return cls.FLOAT
		elif python_type is dict:
			return cls.MAPPING
		elif python_type is NoneType:
			return cls.NULL
		elif python_type is set:
			return cls.SET
		elif python_type is str:
			return cls.STRING
		elif python_type is _PYTHON_FUNCTION_TYPE:
			return cls.FUNCTION
		elif hasattr(python_type, "__origin__"):
			origin_python_type = python_type.__origin__
			maintype = cls.from_type(origin_python_type)
			if origin_python_type in (list, tuple, set):
				if hasattr(python_type, "__args__") and origin_python_type is not tuple:
					valuetype = cls.from_type(python_type.__args__[0])
					return maintype(valuetype)
			if origin_python_type is dict:
				if hasattr(python_type, "__args__"):
					key_type = cls.from_type(python_type.__args__[0])
					value_type = cls.from_type(python_type.__args__[1])
					return maintype(key_type, value_type)
			return maintype
		raise ValueError("can not map python type {0!r} to a compatible data type".format(python_type.__name__))

	@classmethod
	def from_value(cls, python_value):
		"""
		Get the supported data type constant for the specified Python value. If the value can not be mapped to a
		supported data type, then a :py:exc:`TypeError` exception will be raised. This function will not return
		:py:attr:`.UNDEFINED`.

		:param python_value: The native Python value to retrieve the corresponding data type constant for.
		:return: One of the constants.
		"""
		if isinstance(python_value, bool):
			return cls.BOOLEAN
		elif isinstance(python_value, bytes):
			return cls.BYTES
		elif isinstance(python_value, (datetime.date, datetime.datetime)):
			return cls.DATETIME
		elif isinstance(python_value, datetime.timedelta):
			return cls.TIMEDELTA
		elif isinstance(python_value, (decimal.Decimal, float, int)):
			return cls.FLOAT
		elif python_value is None:
			return cls.NULL
		elif isinstance(python_value, (set,)):
			return cls.SET(value_type=iterable_member_value_type(python_value))
		elif isinstance(python_value, (str,)):
			return cls.STRING
		elif isinstance(python_value, collections.abc.Mapping):
			return cls.MAPPING(
				key_type=iterable_member_value_type(python_value.keys()),
				value_type=iterable_member_value_type(python_value.values())
			)
		elif isinstance(python_value, collections.abc.Sequence):
			return cls.ARRAY(value_type=iterable_member_value_type(python_value))
		elif callable(python_value):
			return cls.FUNCTION
		raise TypeError("can not map python type {0!r} to a compatible data type".format(type(python_value).__name__))

	@classmethod
	def is_compatible(cls, dt1, dt2):
		"""
		Check if two data type definitions are compatible without any kind of conversion. This evaluates to ``True``
		when one or both are :py:attr:`.UNDEFINED` or both types are the same. In the case of compound data types (such
		as :py:attr:`.ARRAY`) the member types are checked recursively in the same manner.

		.. versionadded:: 2.1.0

		:param dt1: The first data type to compare.
		:param dt2: The second data type to compare.
		:return: Whether or not the two types are compatible.
		:rtype: bool
		"""
		if not (cls.is_definition(dt1) and cls.is_definition(dt2)):
			raise TypeError('argument is not a data type definition')
		if dt1 is _DATA_TYPE_UNDEFINED or dt2 is _DATA_TYPE_UNDEFINED:
			return True
		if dt1.is_scalar and dt2.is_scalar:
			if isinstance(dt1, DataType.FUNCTION.__class__) and isinstance(dt2, DataType.FUNCTION.__class__):
				if not cls.is_compatible(dt1.return_type, dt2.return_type):
					return False
				if dt1.argument_types != _DATA_TYPE_UNDEFINED and dt2.argument_types != _DATA_TYPE_UNDEFINED:
					if len(dt1.argument_types) != len(dt2.argument_types):
						return False
					if not all(cls.is_compatible(arg1_dt, arg2_dt) for (arg1_dt, arg2_dt) in zip(dt1.argument_types, dt2.argument_types)):
						return False
				if dt1.minimum_arguments != _DATA_TYPE_UNDEFINED and dt2.minimum_arguments != _DATA_TYPE_UNDEFINED:
					if dt1.minimum_arguments != dt2.minimum_arguments:
						return False
				return True
			return dt1 == dt2
		elif dt1.is_compound and dt2.is_compound:
			if isinstance(dt1, DataType.ARRAY.__class__) and isinstance(dt2, DataType.ARRAY.__class__):
				return cls.is_compatible(dt1.value_type, dt2.value_type)
			elif isinstance(dt1, DataType.MAPPING.__class__) and isinstance(dt2, DataType.MAPPING.__class__):
				if not cls.is_compatible(dt1.key_type, dt2.key_type):
					return False
				if not cls.is_compatible(dt1.value_type, dt2.value_type):
					return False
				return True
			elif isinstance(dt1, DataType.SET.__class__) and isinstance(dt2, DataType.SET.__class__):
				return cls.is_compatible(dt1.value_type, dt2.value_type)
		return False

	@classmethod
	def is_definition(cls, value):
		"""
		Check if *value* is a data type definition.

		.. versionadded:: 2.1.0

		:param value: The value to check.
		:return: ``True`` if *value* is a data type definition.
		:rtype: bool
		"""
		return isinstance(value, _DataTypeDef)
