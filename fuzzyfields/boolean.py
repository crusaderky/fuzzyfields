from .core import FuzzyField
from .numbers import Integer
from .errors import FieldTypeError, MalformedFieldError


_BOOL_MAP = {
    'T': True, 'F': False,
    'Y': True, 'N': False,
    'YES': True, 'NO': False,
    'TRUE': True, 'FALSE': False,
    1: True, 0: False,
    True: True, False: False,
}
"""Possible input values
"""

_num_parser = Integer()
"""Preprocessor for string representations of 0 or 1
"""


class Boolean(FuzzyField):
    """A boolean, any string representation of false/true or no/yes, or 0/1.
    """
    def validate(self, value) -> bool:
        """Validate and convert input string

        :param value:
            case-insensitive string representing a boolean:

            - T, Y, Yes, True, 1 equate to True
            - F, N, No, False, 0 equate to False
        :return:
            True|False
        :raise Exception:
            see :meth:`String.validate()`
        """
        orig_value = value

        if isinstance(value, str):
            value = value.upper()

        try:
            return _BOOL_MAP[value]
        except KeyError:
            # Deal with weird string representations of 1/0, e.g. "+1.0"
            pass
        except TypeError:
            # Unhashable type
            raise FieldTypeError(self.name, orig_value, 'boolean')

        # Process string representation of 0/1 e.g. "1", "+1.000"
        # and any other weird use case
        try:
            value = _num_parser.validate(value)
            if value in {0, 1}:
                return bool(value)
        except (MalformedFieldError, FieldTypeError):
            pass

        # Not in _BOOL_MAP and not a string representation of 0/1
        if isinstance(value, (int, str)):
            raise MalformedFieldError(self.name, orig_value, 'boolean')
        raise FieldTypeError(self.name, orig_value, 'boolean')

    @property
    def sphinxdoc(self) -> str:
        return "Boolean (true/false, yes/no, 0/1)"
