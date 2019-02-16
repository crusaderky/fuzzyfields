import decimal
import math
from inspect import getdoc
from pytest import raises
from fuzzyfields import (FuzzyField, MissingFieldError, DuplicateError,
                         MalformedFieldError, FieldTypeError)
from . import requires_pandas


class FooBar(FuzzyField):
    """Stub field that tests that the input is 'foo' and returns 'bar'
    """
    def validate(self, value):
        # Note: we'll never receive None as that is blocked upstream
        if not isinstance(value, str):
            raise FieldTypeError(self.name, value, 'foo')
        if value == 'foo':
            return 'bar'
        raise MalformedFieldError(self.name, value, 'foo')

    @property
    def sphinxdoc(self):
        return "Must be 'foo'"


class Anything(FuzzyField):
    """Anything goes
    """
    def validate(self, value):
        return value

    @property
    def sphinxdoc(self):
        return "Anything goes"


class C:
    """Some class
    """
    x = FooBar(description='my first foo')
    y = FooBar(required=False, unique=True)
    z = FooBar(required=False, default='baz', unique=True)


class D(C):
    w = Anything(unique=True)


X_HELP = """
Name
    x
Type
    FooBar
required
    True
Unique
    False
Description
    Must be 'foo'

    my first foo
""".strip()

Y_HELP = """
Name
    y
Type
    FooBar
required
    False
Default
    None
Unique
    True
Description
    Must be 'foo'
""".strip()

Z_HELP = """
Name
    z
Type
    FooBar
required
    False
Default
    baz
Unique
    True
Description
    Must be 'foo'
""".strip()


def test_doc():
    assert getdoc(C.x) == X_HELP
    assert getdoc(C.y) == Y_HELP
    assert getdoc(C.z) == Z_HELP


def test_property():
    C.y.seen_values.clear()
    C.z.seen_values.clear()

    c = C()

    # Test uninitialised __get__
    with raises(AttributeError) as e:
        c.x
    assert str(e.value) == "Uninitialised property: C.x"

    # Test __get__ -> __set__ round-trip
    # Also test string cleanup in preprocess()
    c.x = '     foo     '
    assert c.x == 'bar'
    assert c.__dict__['x'] == 'bar'

    # Test __del__
    del c.x
    with raises(AttributeError) as e:
        c.x
    assert str(e.value) == "Uninitialised property: C.x"
    c.x = 'foo'
    assert c.x == 'bar'

    # Test Exceptions
    with raises(FieldTypeError) as e:
        c.x = []
    assert str(e.value) == (
        "Field x: Invalid field type: expected foo, got '[]'")
    with raises(MalformedFieldError) as e:
        c.x = 'other'
    assert str(e.value) == (
        "Field x: Malformed field: expected foo, got 'other'")
    with raises(MissingFieldError) as e:
        c.x = None
    assert str(e.value) == 'Field x: Missing or blank field'


def test_parse():
    ff = FooBar()
    assert ff.parse('  foo  ') == 'bar'
    with raises(FieldTypeError) as e:
        ff.parse([])
    assert str(e.value) == (
        "Invalid field type: expected foo, got '[]'")
    with raises(MalformedFieldError) as e:
        ff.parse('other')
    assert str(e.value) == (
        "Malformed field: expected foo, got 'other'")
    with raises(MissingFieldError) as e:
        ff.parse('N/A')
    assert str(e.value) == 'Missing or blank field'

    ff = Anything(required=False, unique=True, default=123)
    assert ff.parse(1) == 1
    assert ff.parse('   N/A   ') == 123
    # Default value doesn't trigger the uniqueness check
    assert ff.parse('   N/A   ') == 123
    with raises(DuplicateError) as e:
        ff.parse(1)
    assert str(e.value) == "Duplicate value: '1'"


def test_not_required():
    C.y.seen_values.clear()
    C.z.seen_values.clear()

    c = C()
    # Read uninitialised non-required fields
    assert c.y is None
    assert c.z == 'baz'
    c.y = 'foo'
    c.z = 'foo'
    assert c.y == 'bar'
    assert c.z == 'bar'
    c.y = None
    c.z = None
    assert c.y is None
    assert c.z == 'baz'


def test_null_values():
    ff = Anything(required=False)
    assert ff.parse(' N/A ') is None
    assert ff.parse('  ') is None
    assert ff.parse(math.nan) is None
    assert ff.parse(decimal.Decimal('nan')) is None


@requires_pandas
def test_null_values_pandas():
    import numpy
    import pandas
    ff = Anything(required=False)
    assert ff.parse(numpy.nan) is None
    assert ff.parse(numpy.datetime64('NaT')) is None
    assert ff.parse(pandas.NaT) is None


def test_unique():
    C.y.seen_values.clear()
    C.z.seen_values.clear()
    D.w.seen_values.clear()

    c = C()
    d = D()

    # FuzzyFields of the same class but different name do not share the same
    # domain
    c.y = 'foo'
    c.z = 'foo'
    with raises(DuplicateError) as e:
        c.y = 'foo'
    assert str(e.value) == "Field y: Duplicate value: 'bar'"

    # Multiple instances of the same class or subclasses share the same domain
    with raises(DuplicateError):
        d.y = 'foo'

    # Default is not tracked on seen_values
    # The seen values are saved _after_ validate()
    c.z = None
    assert C.z.seen_values == {'bar'}

    # Float and int should hit the same hash
    d.w = 1
    with raises(DuplicateError):
        d.w = 1.0
    d.w = 2

    # Track unhashable values
    d.w = [{1: 2}]
    d.w = [{1: 3}]
    with raises(DuplicateError) as e:
        d.w = [{1: 2}]
    assert str(e.value) == "Field w: Duplicate value: '[{1: 2}]'"


def test_instance_override():
    c = C()
    c.x = 'foo'
    with raises(MalformedFieldError):
        c.x = 'other'
    c.x = Anything(required=False)
    c.x = 'other'
    c.x = None
    # Altering the field on the instance did not taint the class
    c = C()
    with raises(MalformedFieldError):
        c.x = 'other'


def test_copy():
    ff1 = Anything(required=False, default='foo')
    ff2 = ff1.copy()
    assert ff2 is not ff1
    assert type(ff2) == Anything
    assert ff2.__dict__ == ff1.__dict__


def test_copy_unique():
    ff1 = Anything(unique=True)
    ff1.parse(1)
    assert ff1.seen_values == {1}
    ff2 = ff1.copy()
    assert ff2.unique is True
    assert ff2.seen_values == set()
    assert ff1.seen_values == {1}
