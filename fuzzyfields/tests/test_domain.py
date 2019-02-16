import pytest
from decimal import Decimal
from fuzzyfields import Domain, DomainError


def test_basic():
    """Hashable and unhashable choices
    """
    ff = Domain(required=False, default='stub', choices=['foo', False, [1]])

    # default does not go through domain validation
    assert ff.parse('N/A') == 'stub'

    assert ff.parse('foo') == 'foo'
    assert ff.parse(False) is False
    assert ff.parse([1]) == [1]

    # Out of domain; case is preserved in message
    with pytest.raises(DomainError) as e:
        ff.parse('hEllo')
    assert str(e.value) == ("value 'hEllo' is not acceptable "
                            "(choices: False,[1],foo)")

    # Out of domain because of case sensitivity
    with pytest.raises(DomainError) as e:
        ff.parse('Foo')
    assert str(e.value) == ("value 'Foo' is not acceptable "
                            "(choices: False,[1],foo)")


def test_case_insensitive():
    ff = Domain(case_sensitive=False, choices=['Foo'])
    # Case is adjusted to the expected value
    assert ff.parse('Foo') == 'Foo'
    assert ff.parse('foo') == 'Foo'

    # Out of domain; case is not altered in the error message
    with pytest.raises(DomainError) as e:
        ff.parse('hEllo')
    assert str(e.value) == "value 'hEllo' is not acceptable (choices: Foo)"


def test_numeric():
    """Numbers are automatically parsed from string and always returned in the
    same type as defined in the choices
    """
    ff = Domain(choices=[1, 2.0, 3 + 4j])

    out = ff.parse(1.0)
    assert out == 1
    assert isinstance(out, int)
    out = ff.parse(" 1.0e0 ")
    assert out == 1
    assert isinstance(out, int)
    out = ff.parse(Decimal(2))
    assert out == 2.0
    assert isinstance(out, float)
    out = ff.parse(3 + 4j)
    assert out == 3 + 4j
    assert isinstance(out, complex)


def test_long_choices():
    """More than 200 chars worth' of choices will be truncated
    """
    ff = Domain(choices=['A' * 80, 'B' * 80, 'C' * 80])
    with pytest.raises(DomainError) as e:
        ff.parse('D')
    assert str(e.value) == ("value 'D' is not acceptable "
                            f"(choices: {'A' * 80},{'B' * 80},"
                            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC...)")


def test_passthrough():
    choices = []
    ff1 = Domain(choices=choices, passthrough=False)
    ff2 = Domain(choices=choices, passthrough=True)

    with pytest.raises(DomainError):
        ff2.parse("foo")

    # Numeric and unhashable
    choices += ["foo", 1, [1]]

    assert ff2.parse("foo") == "foo"
    assert ff2.parse("1.0e0") == 1
    assert ff2.parse([1]) == [1]

    # Non-passthrough Domain was created before choices was populated
    with pytest.raises(DomainError):
        ff1.parse("foo")
