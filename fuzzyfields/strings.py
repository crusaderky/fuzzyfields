import re
from typing import Any
from .core import FuzzyField
from .errors import FieldTypeError, MalformedFieldError


class String(FuzzyField):
    """Any string value
    """
    def validate(self, value: Any) -> str:
        """Validate input string

        :param value:
            input string
        :returns:
            the argument, if it's a string
        :raise FieldTypeError:
            if value is neither a string nor None
        """
        # Note: we'll never receive None as that is blocked upstream
        if not isinstance(value, str):
            raise FieldTypeError(self.name, value, 'string')
        return value

    @property
    def sphinxdoc(self) -> str:
        return """Any string value, stripped of leading and trailing
        whitespace and carriage returns.
        """


class RegEx(FuzzyField):
    """Validate an input string against a regular expression

    :param str pattern:
        regular expression pattern string
    :param kwargs:
        parameters to be passed to :meth:`FuzzyField.__init__`
    :ivar re.Pattern pattern:
        precompiled regex object
    """
    def __init__(self, pattern: str, **kwargs):
        super().__init__(**kwargs)
        self.pattern = re.compile(pattern)

    def validate(self, value: Any) -> str:
        """Validate input string

        :raise FieldTypeError:
            if value is neither a string nor None
        """
        if not isinstance(value, str):
            raise FieldTypeError(self.name, value, 'string')
        if not self.pattern.match(value):
            raise MalformedFieldError(self.name, value,
                                      "'" + self.pattern.pattern + "'")
        return value

    @property
    def sphinxdoc(self) -> str:
        return f"""Any string value, stripped of leading and trailing
        whitespace and carriage returns, that matches the regular expression
        {self.pattern.pattern}
        """


class ISOCodeAlpha(FuzzyField):
    """Letters-only ISO code, e.g. for country or currency.
    Case insensitive (it will be converted to uppercase).

    :param int chars:
        Number of characters of the code (default: 3)
    :ivar int chars:
        as the parameter
    :param kwargs:
        parameters to be passed to :meth:`FuzzyField.__init__`
    """
    chars: int

    def __init__(self, chars: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.chars = chars
        self._re = re.compile(r'^[A-Z]{' + str(chars) + r'}$')

    def validate(self, value: Any) -> str:
        """Validate input string and convert it to uppercase
        """
        if not isinstance(value, str):
            raise FieldTypeError(self.name, value, 'string')
        uvalue = value.upper()
        if not self._re.match(uvalue):
            raise MalformedFieldError(self.name, value, self.sphinxdoc)
        return uvalue

    @property
    def sphinxdoc(self) -> str:
        return f"{self.chars} letters ISO code (case insensitive)"
