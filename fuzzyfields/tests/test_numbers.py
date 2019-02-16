import decimal
import math
import pytest
from fuzzyfields import (Float, Integer, Decimal, Percentage,
                         MalformedFieldError, FieldTypeError,
                         MissingFieldError)


def test_float():
    ff = Float()
    assert ff.parse("1000.1") == 1000.1
    assert ff.parse("-1,000.1") == -1000.1
    assert ff.parse("(1,000.1)") == -1000.1
    assert ff.parse("- 1,000.1 -") == -1000.1
    assert ff.parse("-1,234.5e-6") == -1234.5e-6
    assert ff.parse("-1,234.5E-06") == -1234.5e-6
    assert ff.parse("1,234E006") == 1234.0e6
    assert ff.parse("- 1,234.5e-6 -") == -1234.5e-6
    assert ff.parse("(1,234.5e-6)") == -1234.5e-6
    assert ff.parse('inf') == math.inf
    assert ff.parse('-inf') == -math.inf
    assert ff.parse('- inf -') == -math.inf
    assert ff.parse('(inf)') == -math.inf

    with pytest.raises(FieldTypeError) as e:
        ff.parse([])
    assert str(e.value) == "Invalid field type: expected number, got '[]'"
    with pytest.raises(MalformedFieldError) as e:
        ff.parse('Foo')
    assert str(e.value) == "Malformed field: expected number, got 'Foo'"


def test_decimal():
    ff = Decimal()
    assert ff.parse("1000.1") == decimal.Decimal('1000.1')
    assert ff.parse("-1,000.1") == decimal.Decimal('-1000.1')
    assert ff.parse("(1,000.1)") == decimal.Decimal('-1000.1')
    assert ff.parse("- 1,000.1 -") == decimal.Decimal('-1000.1')
    assert ff.parse("-1,234.5e-6") == decimal.Decimal('-1234.5e-6')
    assert ff.parse("-1,234.5E-06") == decimal.Decimal('-1234.5e-6')
    assert ff.parse("-1,234E006") == decimal.Decimal('-1234.0e6')
    assert ff.parse("- 1,234.5e-6 -") == decimal.Decimal('-1234.5e-6')
    assert ff.parse("(1,234.5e-6)") == decimal.Decimal('-1234.5e-6')
    assert ff.parse('inf') == decimal.Decimal('inf')
    assert ff.parse('-inf') == decimal.Decimal('-inf')
    assert ff.parse('- inf -') == decimal.Decimal('-inf')
    assert ff.parse('(inf)') == decimal.Decimal('-inf')

    # [] raises a different exception than object
    with pytest.raises(FieldTypeError) as e:
        ff.parse(object)
    assert str(e.value) == ("Invalid field type: expected number, got "
                            "'<class 'object'>'")
    with pytest.raises(FieldTypeError) as e:
        ff.parse([])
    assert str(e.value) == "Invalid field type: expected number, got '[]'"
    with pytest.raises(MalformedFieldError) as e:
        ff.parse('Foo')
    assert str(e.value) == "Malformed field: expected number, got 'Foo'"


def test_beautify_decimal():
    """Beautify Decimal('0.00000000') -> Decimal('0E-8') to just Decimal('0')
    But do not accidentally drop numbers before the dot (mantissa or exponent)!
    """
    ff = Decimal()
    assert str(ff.parse("100")) == '100'
    assert str(ff.parse("100.0000")) == '100'
    assert str(ff.parse("0.000000000000")) == '0'
    assert str(ff.parse("100e-40")) == '1.00E-38'
    assert str(ff.parse("100.000000e-40")) == '1.00E-38'
    assert str(ff.parse("100e-39")) == '1.00E-37'
    assert str(ff.parse("100.000001e-40")) == '1.00000001E-38'
    assert str(ff.parse("100E-40")) == '1.00E-38'
    assert str(ff.parse("100.000000E-40")) == '1.00E-38'
    assert str(ff.parse("100.000000E+40")) == '1.00E+42'
    assert str(ff.parse("100.000000E40")) == '1.00E+42'
    assert str(ff.parse("100.000000e40")) == '1.00E+42'
    assert str(ff.parse("100.000001E40")) == '1.00000001E+42'


@pytest.mark.parametrize('value,expect', [
    ('1000.0', 1000),
    ('1000', 1000),
    ('1,000', 1000),
    ('-1000', -1000),
    ('- 1000 -', -1000),
    ('(1000.0)', -1000),
    ('1.2e1', 12),
    ('(120.e-1)', -12),
    ('- 120.e-1 -', -12),
    # inf and -inf are allowed; in these cases the return type is float
    ('inf', math.inf),
    ('-inf', -math.inf),
    ('- inf -', -math.inf),
    ('(inf)', -math.inf),
])
def test_integer(value, expect):
    ff = Integer()
    actual = ff.parse(value)
    assert actual == expect
    assert type(actual) == type(expect)


def test_integer_errors():
    ff = Integer()
    with pytest.raises(FieldTypeError) as e:
        ff.parse([])
    assert str(e.value) == "Invalid field type: expected integer, got '[]'"
    with pytest.raises(MalformedFieldError) as e:
        ff.parse('Foo')
    assert str(e.value) == "Malformed field: expected integer, got 'Foo'"


@pytest.mark.parametrize('value', [
    9999999999999999, '9999999999999999', '999999999999999.9e1',
    decimal.Decimal('9999999999999999')
])
@pytest.mark.parametrize('ff_cls', [Integer, Decimal])
def test_integer_precision(value, ff_cls):
    """Test that Integers and Decimals do not lose precision when a float
    would
    """
    ff = ff_cls()
    expect = 9999999999999999
    assert float(value) != expect
    assert ff.validate(value) == expect


@pytest.mark.parametrize('ff_cls,exp_type', [
    (Float, float), (Integer, int),
    (Decimal, decimal.Decimal), (Percentage, float)
])
@pytest.mark.parametrize('value', [
    '1', '1.0', 1, 1.0, decimal.Decimal('1')
])
def test_output_type(value, ff_cls, exp_type):
    """The FuzzyField always returns the correct type
    """
    ff = ff_cls()
    res = ff.parse(value)
    assert res == 1
    assert isinstance(res, exp_type)


def test_percentage():
    ff = Percentage()
    assert ff.parse('-0.052') == -0.052
    assert ff.parse('- 0.052 -') == -0.052
    assert ff.parse('(0.052)') == -0.052
    # Work around float rounding issue -5.2 / 100 != -0.052
    assert ff.parse('-5.2%') == -5.2 / 100
    assert ff.parse('-5.2 %') == -5.2 / 100
    assert ff.parse('- 5.2% -') == -5.2 / 100
    assert ff.parse('(5.2%)') == -5.2 / 100
    assert ff.parse(-0.052) == -0.052
    assert ff.parse(decimal.Decimal('-0.052')) == -0.052

    with pytest.raises(FieldTypeError) as e:
        ff.parse([])
    assert str(e.value) == "Invalid field type: expected percentage, got '[]'"
    with pytest.raises(MalformedFieldError) as e:
        ff.parse('Foo')
    assert str(e.value) == "Malformed field: expected percentage, got 'Foo'"


@pytest.mark.parametrize('ff_cls,exp_type', [
    (Float, float), (Integer, float),
    (Decimal, decimal.Decimal), (Percentage, float)
])
@pytest.mark.parametrize('value', [
    None, 'N/A', math.nan
])
def test_missing(ff_cls, exp_type, value):
    """Unlike other validators, numbers have NaN as their default (unless
    overridden)"""
    ff = ff_cls(required=False)
    res = ff.parse(value)
    assert math.isnan(res)
    assert isinstance(res, exp_type)
    ff = ff_cls(required=False, default=None)
    assert ff.parse(value) is None


@pytest.mark.parametrize('value', ['nan%', '%', 'N/A%', 'N.A.%'])
def test_percentage_missing(value):
    ff = Percentage()
    with pytest.raises(MissingFieldError) as e:
        ff.parse(value)
    assert str(e.value) == 'Missing or blank field'

    ff = Percentage(required=False)
    assert math.isnan(ff.parse(value))


# TODO: domain
