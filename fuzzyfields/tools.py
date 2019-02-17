import decimal
import math

NA_VALUES = {
    '',
    '#N/A',
    '#N/A N/A',
    '#NA',
    '-1.#IND',
    '-1.#QNAN',
    '-NaN',
    '-nan',
    '1.#IND',
    '1.#QNAN',
    'N/A',
    'NA',
    'NULL',
    'NaN',
    'n/a',
    'nan',
    'null',
    'N.A.',
    'N.A',
}
"""String values interpreted as empty. This is the same set used by
:func:`pandas.read_csv`, with some additions.
"""

try:
    import numpy
    import pandas

    def isnull(x) -> bool:
        """Reimplementation of :func:`pandas.isnull`, with the following
        differences:

        - doesn't require numpy/pandas
        - scalar only
        - guaranteed to return a single bool
        - supports decimal.Decimal
        """
        if isinstance(x, (list, numpy.ndarray)):
            return False
        if isinstance(x, (float, decimal.Decimal)):
            return math.isnan(x)
        return pandas.isnull(x)

except ImportError:
    def isnull(x) -> bool:
        return x is None or (
            isinstance(x, (float, decimal.Decimal)) and math.isnan(x))
