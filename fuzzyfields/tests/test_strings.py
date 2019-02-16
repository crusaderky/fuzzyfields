from pytest import raises
from fuzzyfields import (String, RegEx, ISOCodeAlpha, FieldTypeError,
                         MalformedFieldError)


def test_string():
    ff = String()
    assert ff.parse('   x   ') == 'x'

    with raises(FieldTypeError) as e:
        ff.parse(1)
    assert str(e.value) == "Invalid field type: expected string, got '1'"


def test_regex():
    ff = RegEx(r'foo\d')
    assert ff.parse('     foo3x    ') == 'foo3x'

    with raises(FieldTypeError) as e:
        ff.parse(1)
    assert str(e.value) == "Invalid field type: expected string, got '1'"

    with raises(MalformedFieldError) as e:
        ff.parse('xfoo3')
    assert str(e.value) == (
        "Malformed field: expected 'foo\\d', got 'xfoo3'")


def test_isocodealpha():
    ff = ISOCodeAlpha()
    assert ff.parse('   uSd   ') == 'USD'

    with raises(FieldTypeError) as e:
        ff.parse(1)
    assert str(e.value) == "Invalid field type: expected string, got '1'"

    with raises(MalformedFieldError) as e:
        ff.parse('us')
    assert str(e.value) == ("Malformed field: expected 3 letters ISO code "
                            "(case insensitive), got 'us'")

    ff = ISOCodeAlpha(chars=2)
    assert ff.parse('us') == 'US'
