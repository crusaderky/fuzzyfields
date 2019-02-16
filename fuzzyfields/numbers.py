import decimal
import math
import re
from typing import Any, Union
from .core import FuzzyField, NA_VALUES
from .errors import DomainError, FieldTypeError, MalformedFieldError


try:
    import numpy
    CAN_CAST_TO_INT = str, numpy.integer
except ImportError:
    CAN_CAST_TO_INT = str


class Float(FuzzyField):
    """Convert a string representing a number, an int, or other numeric types
    (e.g. `numpy.float64`) to float.

    :param default:
        Default value. Unlike in all other FuzzyFields, if omitted it is NaN
        instead of None.
    :param min_value:
        Minimum allowable value. Omit for no minimum.
    :param max_value:
        Maximum allowable value. Omit for no maximum.
    :param bool allow_min:
        If True, test that value >= min_value, otherwise value > min_value
    :param bool allow_max:
        If True, test that value <= max_value, otherwise value < max_value
    :param bool allow_zero:
        If False, test that value != 0
    :param dict kwargs:
        parameters to be passed to :class:`FuzzyField`
    """
    min_value: Union[int, float]
    max_value: Union[int, float]
    allow_min: bool
    allow_max: bool
    allow_zero: bool

    def __init__(self, *, min_value: Union[int, float] = -math.inf,
                 max_value: Union[int, float] = math.inf,
                 allow_min: bool = True, allow_max: bool = True,
                 allow_zero: bool = True, default: Any = math.nan, **kwargs):
        super().__init__(default=default, **kwargs)

        assert min_value <= max_value
        self.min_value = min_value
        self.max_value = max_value
        self.allow_min = allow_min
        self.allow_max = allow_max
        self.allow_zero = allow_zero

    def validate(self, value: Any) -> Union[float, int, decimal.Decimal, None]:
        """Convert a number or a string representation of a number to a
        validated number.

        :param value:
            string representing a number, possibly with thousands separator
            or in accounting negative format, e.g. (5,000.200) ==> -5000.2,
            or any number-like object
        :rtype:
            as returned by :meth:`Numeric.num_converter`
        :raises DomainError:
            Number out of allowed range
        :raises MalformedFieldError, FieldTypeError:
            Not a number
        """
        if isinstance(value, str):
            # Preprocess strings before passing them to self._num_converter
            # Remove thousands separator
            value = value.replace(',', '')

            # Convert accounting-style negative numbers, e.g. '(1000)'
            if value.startswith('(') and value.endswith(')'):
                value = '-' + value[1:-1]

            # Convert negative numbers formatted by Excel in some cases
            # '- 1000 -'
            elif value.startswith('- ') and value.endswith(' -'):
                value = '-' + value[2:-2]

        value = self._num_converter(value)
        if value is None:
            return None

        # Decimal has problems comparing to float/int
        valuef = float(value)

        if ((not self.allow_zero and valuef == 0)
                or (self.allow_min and valuef < self.min_value)
                or (not self.allow_min and valuef <= self.min_value)
                or (self.allow_max and valuef > self.max_value)
                or (not self.allow_max and valuef >= self.max_value)):
            raise DomainError(self.name, value, choices=self.domain_str)

        return value

    @property
    def domain_str(self) -> str:
        """String representation of the allowed domain, e.g. "]-1, 1] non-zero"
        """
        lbracket = '[' if self.allow_min else ']'
        rbracket = ']' if self.allow_max else '['
        msg = f'{lbracket}{self.min_value}, {self.max_value}{rbracket}'
        if not self.allow_zero:
            msg += ' non-zero'
        return msg

    def _num_converter(self, value: Any) -> float:
        """Convert string, int, or other to float
        """
        try:
            return float(value)
        except TypeError:
            raise FieldTypeError(self.name, value, "number")
        except ValueError:
            raise MalformedFieldError(self.name, value, "number")

    @property
    def sphinxdoc(self) -> str:
        return f"Any number in the domain {self.domain_str}"


class Decimal(Float):
    """Convert a number or a string representation of a number to
    :class:`~decimal.Decimal`, which is much much slower and heavier than float
    but avoids converting 3.1 to 3.0999999.
    """
    def __init__(self, *, default: Any = decimal.Decimal('nan'), **kwargs):
        super().__init__(default=default, **kwargs)

    def _num_converter(self, value: Any) -> decimal.Decimal:
        """Convert string, float, or int to decimal.Decimal
        """
        # Performance shortcut
        if isinstance(value, decimal.Decimal):
            return value

        orig_value = value
        # Remove leading zeros after comma, as they confuse Decimal
        # e.g.  Decimal('0.0000000000') -> Decimal("0E-10")
        # Do not accidentally drop leading zeros in the exponent.
        if isinstance(value, str):
            value = value.upper()
            if 'E' in value:
                # Scientific notation
                mantissa, _, exponent = value.partition('E')
                if '.' in mantissa:
                    mantissa = re.sub(r'0*$', '', mantissa)
                value = f'{mantissa}E{exponent}'
            elif '.' in value:
                # Not scientific notation
                value = re.sub(r'0*$', '', value)

        try:
            return decimal.Decimal(value)
        except (TypeError, ValueError):
            raise FieldTypeError(self.name, orig_value, "number")
        except decimal.InvalidOperation:
            raise MalformedFieldError(self.name, orig_value, "number")


class Integer(Float):
    """Whole number.

    Valid values are:

    - anything that is parsed by the `int` constructor.
    - floats with strictly trailing zeros (e.g. 1.0000)
    - scientific format as long as there are no digits below 10^0 (1.23e2)

    .. note::
       inf and -inf are valid inputs, but in these cases
       the output will be of type float. To disable them you can use

       - ``min_value=-math.inf, allow_min=False``
       - ``max_value=math.inf, allow_max=False``

       NaN is treated as an empty cell, so it is accepted if required=False;
       in that case the validation will return whatever is set for default,
       which is math.nan unless overridden, which makes it a third case where
       the output value won't be int but float.

    :raises MalformedFieldError:
        if the number can't be cast to int without losing precision
    """
    def _num_converter(self, value: Any) -> Union[int, float]:
        """Convert value to int
        """
        # Quick exit
        if isinstance(value, int):
            return value

        # Attempt quick conversion. This won't work in case of the more
        # sophisticated cases we want to cover, e.g. '1.0e1'.
        # DO NOT blindly convert to int if value is a float, as int(3.5) = 3!
        # Not passing by float also prevents precision loss issues, e.g.
        # int('9999999999999999') != float('9999999999999999')
        if isinstance(value, CAN_CAST_TO_INT):
            try:
                return int(value)
            except ValueError:
                pass

        # float, np.float32/64, or string representation of a float
        try:
            valued = decimal.Decimal(value)
        except (TypeError, ValueError):
            raise FieldTypeError(self.name, value, "integer")
        except decimal.InvalidOperation:
            raise MalformedFieldError(self.name, value, "integer")

        # This should be already catered for by :meth:`FuzzyField.preprocess`
        assert not math.isnan(valued)
        if math.isinf(valued):
            return float(valued)

        valuei = int(valued)
        if valuei != valued:
            # Mantissa after the dot is not zero
            raise MalformedFieldError(self.name, value, "integer")
        return valuei

    @property
    def sphinxdoc(self) -> str:
        return f"Any whole number in the domain {self.domain_str}"


class Percentage(Float):
    """Percentage, e.g. 5% or .05

    .. warning::
       There's nothing stopping somebody from writing "35" where it should have
       been either "35%" or "0.35". If this field receives "35", it will
       return 3500.0. You should use the min_value and max_value parameters of
       :class:`Float` to prevent this kind of incidents. Still, nothing will
       ever protect you from a "1", which will be converted to 1.00 but the
       author of the input may have wanted to say 0.01.
    """
    def _num_converter(self, value: Any) -> Union[float, None]:
        """Convert string, int, or other to float
        """
        try:
            if isinstance(value, str) and value[-1] == '%':
                value = value[:-1].strip()
                if value in NA_VALUES:
                    return None
                return float(value) / 100
            return float(value)
        except TypeError:
            raise FieldTypeError(self.name, value, "percentage")
        except ValueError:
            raise MalformedFieldError(self.name, value, "percentage")

    @property
    def sphinxdoc(self) -> str:
        return f"Percentage, e.g. 5% or 0.05, in the domain {self.domain_str}"
