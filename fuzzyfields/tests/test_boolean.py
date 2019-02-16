from decimal import Decimal
from pytest import raises
from fuzzyfields import Boolean, FieldTypeError, MalformedFieldError


def test_ok():
    ff = Boolean()
    # Bool
    assert ff.parse(True) is True
    assert ff.parse(False) is False
    # Numbers
    assert ff.parse(1) is True
    assert ff.parse(0) is False
    assert ff.parse(1.0) is True
    assert ff.parse(0.0) is False
    assert ff.parse(-0.0) is False
    assert ff.parse(Decimal('1.0')) is True
    assert ff.parse(Decimal('0.0')) is False
    assert ff.parse(Decimal('-0.0')) is False
    # String representation of numbers
    assert ff.parse('  1.0e0  ') is True
    assert ff.parse('  -0.0e0  ') is False
    # Other strings
    assert ff.parse('  trUe  ') is True
    assert ff.parse('  faLSe  ') is False
    assert ff.parse('  yEs  ') is True
    assert ff.parse('  nO  ') is False
    assert ff.parse('  t  ') is True
    assert ff.parse('  f  ') is False
    assert ff.parse('  T  ') is True
    assert ff.parse('  F  ') is False
    assert ff.parse('  y  ') is True
    assert ff.parse('  n  ') is False
    assert ff.parse('  Y  ') is True
    assert ff.parse('  N  ') is False


def test_malformed():
    ff = Boolean()

    class C:
        def __repr__(self):
            return 'someC'

    # Arbitrary class
    with raises(FieldTypeError) as e:
        ff.parse(C())
    assert str(e.value) == "Invalid field type: expected boolean, got 'someC'"

    # Unhashable
    with raises(FieldTypeError) as e:
        ff.parse([])
    assert str(e.value) == "Invalid field type: expected boolean, got '[]'"

    # Other strings or numbers
    with raises(MalformedFieldError) as e:
        ff.parse('Nope')
    assert str(e.value) == "Malformed field: expected boolean, got 'Nope'"

    with raises(MalformedFieldError) as e:
        ff.parse(-1)
    assert str(e.value) == "Malformed field: expected boolean, got '-1'"

    with raises(MalformedFieldError) as e:
        ff.parse(-1.0)
    assert str(e.value) == "Malformed field: expected boolean, got '-1.0'"

    with raises(MalformedFieldError) as e:
        ff.parse('-1')
    assert str(e.value) == "Malformed field: expected boolean, got '-1'"
