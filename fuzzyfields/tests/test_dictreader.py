import csv
import io
import pytest
from fuzzyfields import DictReader, String, Float, ISOCodeAlpha


class SampleReader(DictReader):
    """Reader used for tests
    """
    fields = {
        'owner': String(unique=True),
        'price': Float(),
        'currency': ISOCodeAlpha(required=False, default='GBP'),
    }
    errors = 'error'
    name_map = {'owner': 'user'}


INPUT_ROWS = [
    # OK line. Notice the whitespaces that will be removed automatically.
    # Also notice the None key, which is yielded by csv.DictReader when
    # there's unexpected data
    {'price': '11.2', '  currency  ': '  EUR  ', 'owner': 'John',
     'other': 'blah', None: 'blah'},
    # Duplicate line when converting to dict using 'currency' as the key
    {'price': '15.7', 'currency': 'EUR', 'owner': 'Jack'},
    # Fall back to default currency. Unexpected column 'other' is silently
    # ignored.
    {'price': '1,000.7', 'currency': 'N/A', 'owner': 'Bill', 'other': 'blah'},
    # currency was the last column but the data row in input to csv.DictReader
    # was shorter than the header row. Hence, csv.DictReader yields None.
    {'price': '2,000.0', 'currency': None, 'owner': 'Jane'},
    # Empty row. Blanks are silently ignored without raising an error.
    {'price': '  ', 'currency': '  ', 'owner': None},
    # Error price; price is required so the whole row is discarded
    {'price': 'N/A', 'currency': 'USD', 'owner': 'Sam'},
    # Error currency; currency is not requires so the error is reported and
    # the cell is replaced with the default
    {'price': 100, 'currency': 'Pounds', 'owner': 'Todd'},
    # Duplicate required cell 'owner'
    # Note how the initial row was discarded because of an error, but this
    # won't stop the duplication check
    {'price': 100, 'currency': 'USD', 'owner': 'Sam'},
    # 2 errors in a line: invalid currency, no price
    {'currency': 'blah', 'owner': 'Joe'}
]

OUTPUT_ROWS = [
    {'currency': 'EUR', 'price': 11.2, 'user': 'John'},
    {'currency': 'EUR', 'price': 15.7, 'user': 'Jack'},
    {'currency': 'GBP', 'price': 1000.7, 'user': 'Bill'},
    {'currency': 'GBP', 'price': 2000, 'user': 'Jane'},
    {'currency': 'GBP', 'price': 100, 'user': 'Todd'},
]

LOGLINES = [
    ('root', 40, 'At record 5: Field price: Missing or blank field'),
    ('root', 40, "At record 6: Field currency: Malformed field: expected 3 "
                 "letters ISO code (case insensitive), got 'Pounds'"),
    ('root', 40, "At record 7: Field owner: Duplicate value: 'Sam'"),
    ('root', 40, 'At record 8: Field price: Missing or blank field'),
    ('root', 40, "At record 8: Field currency: Malformed field: expected 3 "
                 "letters ISO code (case insensitive), got 'blah'"),
]

LOGLINES_CSV = [
    ('root', 40, 'At line 7: Field price: Missing or blank field'),
    ('root', 40, "At line 8: Field currency: Malformed field: expected 3 "
                 "letters ISO code (case insensitive), got 'Pounds'"),
    ('root', 40, "At line 9: Field owner: Duplicate value: 'Sam'"),
    ('root', 40, 'At line 10: Field price: Missing or blank field'),
    ('root', 40, "At line 10: Field currency: Malformed field: expected 3 "
                 "letters ISO code (case insensitive), got 'blah'"),
]


# Run test twice to verify that uniqueness checks are reset when parsing a
# new file
@pytest.mark.parametrize('round', [1, 2])
def test_parse(caplog, round):
    reader = SampleReader(INPUT_ROWS)
    assert reader.record_num == -1
    rows = list(reader)
    assert reader.record_num == 8
    assert rows == OUTPUT_ROWS
    assert caplog.record_tuples == LOGLINES


def test_csv_roundtrip(caplog):
    """Same as test_parse, but log lines change to reflect actual row
    numbers on the file. Also test the line_num property.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, ['owner', 'price', 'currency', 'other'])
    writer.writeheader()
    for row in INPUT_ROWS:
        writer.writerow({k.strip(): v for k, v in row.items()})
    buf.seek(0)
    reader = SampleReader(csv.DictReader(buf))
    assert reader.record_num == -1
    assert reader.line_num == 0
    rows = list(reader)
    assert reader.record_num == 8
    assert reader.line_num == 10
    assert rows == OUTPUT_ROWS
    assert caplog.record_tuples == LOGLINES_CSV


# TODO: preprocess_row(), postprocess_row()
# TODO: __init__ params
# TODO: errors='raise'
# TODO: errors=debug, info, warning, critical
# TODO: errors=callable(exc)
# TODO: passthrough domain
