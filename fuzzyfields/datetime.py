import datetime
import warnings
from typing import Dict, Any
from .fuzzyfield import FuzzyField
from .errors import FieldTypeError, MalformedFieldError


class Timestamp(FuzzyField):
    """Parse and check various date and time formats

    .. note::
       This field requires `pandas <https://pandas.pydata.org>`_.

    :param str output:
        Format of the output value. Possible values are:

        'pandas' (default)
            return type is :class:`pandas.Timestamp`

            .. warning::
               This format is limited to the period between
               1677-09-22 and 2262-04-11, see `pandas documentation
               <http://pandas.pydata.org/pandas-docs/stable/timeseries.html#timestamp-limitations>`_.
               Timestamps outside of this range will be automatically coerced
               to its edges.
        'datetime'
            return type is :class:`datetime.datetime`
        'numpy'
            return type is `numpy.datetime64`
        any other string
            anything else will be interpreted as a format string for
            :meth:`pandas.Timestamp.strftime`;
            e.g. ``%Y/%m/%d`` will produce a string YYYY/MM/DD.
    :param bool required:
        See :class:`FuzzyField`
    :param default:
        See :class:`FuzzyField`
    :param str description:
        See :class:`FuzzyField`
    :param bool unique:
        See :class:`FuzzyField`
    :param kwargs:
        Parameters to be passed to :func:`pandas.to_datetime`.

        .. note::
           The default is to set dayfirst=True, meaning that in case of
           ambiguity this function will choose the European format DD/MM/YYYY,
           whereas the default for :func:`pandas.to_datetime` is dayfirst=False
           (American format MM/DD/YYYY).
    """
    output: str
    pandas_kwargs: Dict[str, Any]

    def __init__(self, *, output: str = 'pandas', required: bool = True,
                 default=None, description: str = None, unique: bool = False,
                 **kwargs):
        import pandas  # noqa: F401

        super().__init__(required=required, default=default,
                         description=description, unique=unique)
        if '%' not in output and output not in ('pandas', 'datetime', 'numpy'):
            raise ValueError("output: expected 'pandas', 'datetime', 'numpy', "
                             "or format string; got %s" % output)
        self.output = output
        kwargs.setdefault('dayfirst', True)
        self.pandas_kwargs = kwargs

    def validate(self, value):
        """Validate and convert input

        :param value:
            Anything recognized by :func:`pandas.to_datetime`
        :return:
            parsed date, depending on the 'output' parameter
        """
        import pandas

        try:
            value = pandas.to_datetime(value, **self.pandas_kwargs)
        except pandas.errors.OutOfBoundsDatetime as e:
            # The timestamp has been parsed and is stored in the exception
            # message; it just can't be coerced into a pandas.Timestamp
            value = ' '.join(str(e).split()[-2:])
            return self._parse_outofbounds(value)
        # OutOfBoundsDateTime is a subclass of ValueError so it must appear
        # higher in the list
        except ValueError:
            raise MalformedFieldError(self.name, value, "date")
        except TypeError:
            raise FieldTypeError(self.name, value, "date")

        if self.output == 'pandas':
            return value
        elif self.output == 'numpy':
            return value.to_datetime64()
        elif self.output == 'datetime':
            return value.to_pydatetime()
        else:
            return value.strftime(self.output)

    def _parse_outofbounds(self, value):
        """Deal with dates out of the range supported by pandas.Timestamp

        :param str value:
            YYYY-MM-DD hh:mm:ss
        :returns:
            parsed value depending on self.output
        """
        import numpy
        import pandas

        if self.output == 'pandas':
            # Force to either Timestamp.min or Timestamp.max as of 00:00:00
            # to avoid confusing processes that expects exact days.
            if value < '1677-09-22':
                new_value = '1677-09-22'
            elif value > '2262-04-11':
                new_value = '2262-04-11'
            else:
                assert False

            warnings.warn('Timestamp %s is out of bounds; '
                          'forcing it to %s' % (value, new_value))
            return pandas.to_datetime(new_value)
        elif self.output == 'numpy':
            return numpy.datetime64(value)
        elif self.output == 'datetime':
            return datetime.datetime.strptime(
                value, '%Y-%m-%d %H:%M:%S')
        else:
            return pandas.Period(value).strftime(self.output)

    @property
    def sphinxdoc(self) -> str:
        return "Any date/time representation"
