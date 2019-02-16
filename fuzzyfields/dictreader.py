import logging
from typing import Any, Dict, Union, Callable, Iterable
from .core import FuzzyField
from .errors import ValidationError


class DictReader:
    """Generic iterable that acquires an iterable of dicts in input, e.g.
    :class:`csv.DictReader`, and for every input line it yields a line that is
    filtered, validated and processed depending on the input parameters.

    :param iterable:
        an iterable object, e.g. :class:`csv.DictReader`, that yields dicts of
        {field : value}

    :param fields:
        dict of instance-specific :class:`FuzzyField` objects.
        You should *not* use this parameter to set any fields that are known at
        the time of writing the code, which is the most common use case.
        Instead, you should create a subclass of DictReader and override the
        DictReader.fields class attribute.

    :param errors:
        One of:

        'raise' (default)
            raise a :class:`ValidationError` on the first line
        'critical', 'error', 'warning', 'info', 'debug'
            log the error with the mathing functions in :mod:`logging` and
            continue
        callable(:class:`~fuzzyfields.ValidationError`)
            invoke a custom callable and continue (unless it itself raises an
            Exception)

        In case errors != 'raise' and a FuzzyField raises an exception,

        - if the field is required, the entire line is discarded
        - otherwise, the field is replaced with its default value\

        Alternatively to passing this parameter, you may create a subclass of
        DictReader and override the DictReader.errors class attribute.

    :param dict name_map:
        optional dict of {from name: to name} renames, where each pair
        performs a key replacement.

        Alternatively to passing this parameter, you may create a subclass of
        DictReader and override the DictReader.name_map class attribute.

    :ivar int record_num:
        current record (counting from 0), or -1 if the iteration hasn't started
        yet.
    """
    fields: Dict[str, FuzzyField] = {}
    """Class-level map of ``{field name: FuzzyField}``. Overriding this dict is
    the preferential way to add fields, as they will dynamically build Sphinx
    documentation. You may add instance-specific fields with the matching
    ``__init__`` parameter. Override with a :class:`~collections.OrderedDict`
    if you need the fields to be parsed in order (this is generally only
    necessary when one field defines the domain of another).
    """

    errors: Union[str, Callable[[Exception], Any]] = 'raise'
    """Class-level error handling system. See class-level documentation.
    Can be overridden through the matching ``__init__`` parameter.
    """

    name_map: Dict[str, str] = {}
    """Class-level map of field renames. The keys in this dict must be
    a subset of the keys in the fields dict.
    You can add to this dict in an instance-specific way by setting the
    matching ``__init__`` parameter.
    """

    def __init_subclass__(cls):
        """Executed after all subclasses of the current class are defined. Set
        FuzzyField.name and enrich the docstring of the subclass with the
        documentation of the fields.
        """
        if cls.__doc__:
            cls.__doc__ = cls.__doc__.strip() + '\n\n'
        else:
            cls.__doc__ = ''
        cls.__doc__ += '**Fields**\n'

        for k, v in sorted(cls.fields.items()):
            v.owner = cls
            v.name = k
            cls.__doc__ += f'\n{k}\n'
            for line in repr(v).splitlines():
                cls.__doc__ += f'    {line}\n'

    def __init__(self, iterable: Iterable,
                 fields: Dict[str, FuzzyField] = None, *,
                 errors: Union[str, Callable[[Exception], Any]] = None,
                 name_map: Dict[str, str] = None):
        """Build new object
        """
        self.iterable = iterable
        self.record_num = -1

        # Create instance-specific copy of fields
        self.fields = {k: v.copy() for k, v in self.fields.items()}
        if fields is not None:
            self.fields.update(fields)
        for k, v in self.fields.items():
            v = v.copy()
            v.owner = type(self)
            v.name = k
            self.fields[k] = v

        if errors is not None:
            self.errors = errors
        if isinstance(self.errors, str) and self.errors not in {
                'debug', 'info', 'warning', 'error', 'critical', 'raise'}:
            raise ValueError("errors: expected log level, 'raise', "
                             "or callable; got %s" % self.errors)

        if name_map is not None:
            self.name_map = self.name_map.copy()
            self.name_map.update(name_map)
        name_map_check = self.name_map.keys() - self.fields.keys()
        if name_map_check:
            raise KeyError("Key(s) in name_map not found in fields: "
                           + ", ".join(sorted(name_map_check)))

    def _error_handler(self, exc: ValidationError) -> None:
        """Deal with a validation failure

        :param ValidationError exc:
            error raised by an individual FuzzyField
        """
        exc.record_num = self.record_num
        try:
            exc.line_num = self.line_num
        except AttributeError:
            # self.iterable is not a csv.DictReader or compatible class
            pass
        if self.errors == 'raise':
            raise exc
        elif isinstance(self.errors, str):
            logfn = getattr(logging, self.errors)
            logfn("%s", exc)
        else:
            self.errors(exc)

    def __iter__(self):
        """Draw dicts from the underlying iterable and yield dicts of
         {field name : parsed value}
        """
        for self.record_num, row in enumerate(self.iterable):

            # Give child classes a chance to alter the row before parsing it
            row = self.preprocess_row(row)
            if row is None:
                continue

            # csv.DictReader stores unexpected columns under the None key.
            # Discard them.
            row.pop(None, None)
            # Skip completely blank rows
            if all(isinstance(cell, str) and not cell.strip() or cell is None
                   for cell in row.values()):
                continue
            # Strip spurious whitespace from column headers
            row = {k.strip(): v for k, v in row.items()}

            out = {}
            required_field_error = False

            # Parse each field. If a field fails to parse:
            # - If there is no error handler, raise an Exception immediately.
            # - If there's an error handler and the field is not required,
            #   the field is replaced with its default value.
            # - If there's an error handler and the field is required,
            #   all fields are parsed and finally the line is skipped.
            for field in self.fields.values():
                # Apply name mapping
                out_name = self.name_map.get(field.name, field.name)

                try:
                    # Entirely missing columns are OK as long as they pertain
                    # to non-required fields
                    value = row.get(field.name, None)
                    out[out_name] = field.parse(value)

                except ValidationError as exc:
                    self._error_handler(exc)

                    if field.required:
                        required_field_error = True
                    else:
                        out[out_name] = field.default

            # If a required field has an error, discard the whole line
            if required_field_error:
                continue

            # Give child classes a chance to alter the row before pushing it
            # out
            out = self.postprocess_row(out)
            if out is None:
                continue

            yield out

    @property
    def line_num(self) -> int:
        """Return line number of underlying file.

        :raises AttributeError:
            if the underlying iterator is not a :class:`csv.reader`,
            :class:`csv.DictReader`, or another duck-type compatible class
        """
        return self.iterable.line_num

    def preprocess_row(self, row) -> Dict[str, Any]:
        """Give child classes an opportunity to pre-process every row before
        feeding it to the FuzzyFields. This allows handling special cases.

        You must use this method to manipulate the row if the underlying
        iterator does not natively yields dicts, e.g. a csv.reader object.

        :param row:
            The row as read by self.iterable, with all names and
            before name mapping
        :return:
            modified row, or None if the row should be skipped
        """
        return row

    def postprocess_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Give child classes an opportunity to post-process every row after
        it's been parsed by the FuzzyFields. This allows handling special
        cases and performing cross-field validation.

        :param row:
            The row as composed by the fields, after name mapping
        :return:
            Modified row, or None if the row should be skipped
        """
        return row
