import datetime
import pytest
from fuzzyfields import Timestamp, MalformedFieldError
from . import has_pandas, requires_pandas

if has_pandas:
    import numpy
    import pandas
else:
    class numpy:
        @classmethod
        def datetime64(cls, x):
            pass

    class pandas:
        @classmethod
        def to_datetime(cls, x):
            pass


@requires_pandas
@pytest.mark.parametrize('value', [
    'not a date', '10/notAMonth/2016',
    '2016-00-01', '2016-13-13', '2016-01-00', '2016-02-30'
])
def test_malformed(value):
    v = Timestamp()
    with pytest.raises(MalformedFieldError) as e:
        v.parse(value)
    assert str(e.value) == f"Malformed field: expected date, got '{value}'"


@requires_pandas
@pytest.mark.parametrize('dayfirst', [False, True])
@pytest.mark.parametrize('yearfirst', [False, True])
@pytest.mark.parametrize('value', [
    '11 March 2016', '11th March 2016', 'March 11th 2016', '11 mar 2016',
    '2016-03-11', '2016/03/11', '2016.03.11', '20160311',
])
def test_unambiguous(dayfirst, yearfirst, value):
    expect = pandas.to_datetime('11 March 2016')
    v = Timestamp(dayfirst=dayfirst, yearfirst=yearfirst)
    assert v.parse(value) == expect


@requires_pandas
def test_ambiguous():
    """European notation is preferred to the American one by default
    """
    expect = pandas.to_datetime('10 nov 2012')
    v = Timestamp()
    assert v.parse('10/11/2012') == expect
    assert v.parse('10/11/12') == expect
    assert v.parse('10-11-12') == expect
    assert v.parse('10.11.12') == expect

    v = Timestamp(dayfirst=False)
    assert v.parse('11/10/12') == expect


@requires_pandas
def test_leapyear():
    v = Timestamp()
    with pytest.raises(MalformedFieldError) as e:
        v.parse('2015/02/29')
    assert str(e.value) == "Malformed field: expected date, got '2015/02/29'"

    assert v.parse('2016/02/29') == pandas.to_datetime('29 feb 2016')


@requires_pandas
@pytest.mark.parametrize('output,expect', [
    ('pandas', pandas.to_datetime('2012-11-10')),
    ('numpy', numpy.datetime64('2012-11-10')),
    ('datetime', datetime.datetime(2012, 11, 10)),
    ('%Y/%m/%d', '2012/11/10'),
    ('%m %Y', '11 2012'),
])
def test_format(output, expect):
    v = Timestamp(output=output)
    assert v.parse('10/11/12') == expect


@requires_pandas
@pytest.mark.parametrize('value,expect', [
    ('1677-09-21', '1677-09-22'),
    ('1677-09-22', '1677-09-22'),
    ('1677-09-23', '1677-09-23'),
    ('2262-04-10', '2262-04-10'),
    ('2262-04-11', '2262-04-11'),
    ('2262-04-12', '2262-04-11'),
])
def test_outofbounds_pandas(value, expect, recwarn):
    v = Timestamp()
    assert v.parse(value) == pandas.to_datetime(expect)
    if value == expect:
        assert not recwarn
    else:
        assert len(recwarn) == 1
        assert str(recwarn.pop().message) == (
            f'Timestamp {value} 00:00:00 is out of bounds; forcing it to '
            f'{expect}')


@requires_pandas
@pytest.mark.parametrize('output,value,expect', [
    ('numpy', '1000-01-01', numpy.datetime64('1000-01-01')),
    ('numpy', '5000-01-01', numpy.datetime64('5000-01-01')),
    ('datetime', '1000-01-01', datetime.datetime(1000, 1, 1)),
    ('datetime', '5000-01-01', datetime.datetime(5000, 1, 1)),
    ('%Y-%m-%d', '1000-01-01', '1000-01-01'),
    ('%Y-%m-%d', '5000-01-01', '5000-01-01'),
])
def test_outofbounds_notpandas(output, value, expect, recwarn):
    """Only output='pandas' has the problem of clipping
    """
    v = Timestamp(output=output)
    assert v.parse(value) == expect
    assert not recwarn
