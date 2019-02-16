"""All Exceptions raised by the package
"""
from typing import Any, Union


class ValidationError(Exception):
    """Common ancestor of all landg.validators exceptions

    :param str name:
        :class`FuzzyField` name
    :ivar int line_num:
        Line number of the underlying file, if available
        Set by :class:`~fuzzyfields.DictReader`.
    :ivar int record_num:
        Record number as counted by :class:`~fuzzyfields.DictReader`

    .. note::
       Whenever a subclass of Exception is unpickled, its __init__ method is
       invoked with no arguments,, and *then* __setstate__ recovers the
       contents. So one must be very careful to allow the __init__ method to
       work with a single, dummy value.
    """
    name: Union[str, None]
    line_num: Union[int, None]
    record_num: Union[int, None]

    def __init__(self, name: Union[str, None] = None):
        self.name = name
        self.line_num = None
        self.record_num = None

    @property
    def prefix(self) -> str:
        if self.line_num is not None:
            res = f"At line {self.line_num}: "
        elif self.record_num is not None:
            res = f"At record {self.record_num}: "
        else:
            res = ''
        if self.name:
            res = f'{res}Field {self.name}: '
        return res

    def __str__(self)-> str:
        return repr(self)


class MalformedFieldError(ValidationError):
    """Parsed malformed field

    .. note::
       See note in parent class about pickling
    """
    value: Any
    expect: Any

    def __init__(self, name: Union[str, None], value: Any = None,
                 expect: Any = None):
        super().__init__(name)
        self.value = value
        self.expect = expect

    def __repr__(self)-> str:
        return (f"{self.prefix}Malformed field: expected "
                f"{self.expect}, got '{self.value}'")


class FieldTypeError(ValidationError):
    """Parsed field of invalid type

    .. note::
       See note in parent class about pickling
    """
    value: Any
    expect: Any

    def __init__(self, name: Union[str, None], value: Any = None,
                 expect: Any = None):
        super().__init__(name)
        self.value = value
        self.expect = expect

    def __repr__(self) -> str:
        return (f"{self.prefix}Invalid field type: expected "
                f"{self.expect}, got '{self.value}'")


class DuplicateError(ValidationError):
    """When unique=True, an identical value appears twice for the same field,
    or a duplicate value was found when invoking
    :meth:`fuzzyfields.DictReader.to_dict()`.

    .. note::
       See note in parent class about pickling
    """
    value: Any

    def __init__(self, name: Union[str, None], value: Any = None):
        super().__init__(name)
        self.value = value

    def __repr__(self):
        return f"{self.prefix}Duplicate value: '{self.value}'"


class DomainError(ValidationError):
    """Value is not among the permissible ones

    .. note::
       See note in parent class about pickling
    """
    value: Any
    choices: Any

    def __init__(self, name: Union[str, None], value: Any = None,
                 choices: Any = None):
        super().__init__(name)
        self.value = value
        self.choices = choices

    def __repr__(self) -> str:
        return (f"{self.prefix}value '{self.value}' is not acceptable "
                f"(choices: {self.choices})")


class MissingFieldError(ValidationError):
    """Field is null and required is True, or a dict key (typically a column
    header) is missing from the value returned by the input
    :class:`~fuzzyfields.DictReader`

    .. note::
       See note in parent class
    """
    def __repr__(self) -> str:
        return f"{self.prefix}Missing or blank field"
