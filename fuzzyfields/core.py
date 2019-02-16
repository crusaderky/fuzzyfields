import decimal
import math
import pickle
from typing import Any
from .errors import MissingFieldError, DuplicateError

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

        - doesn't mandatorily require numpy/pandas
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


class FuzzyField:
    """Abstract base class.

    :param bool required:
        If False, return default if value is "" or "N/A".
        If True, ensure that this field has a value,
    :param default:
        Default value to return in case required is False and value is None,
        NaN, NaT, empty string, "N/A", or similar (basically anything for which
        :func:`pandas.isnull` returns True, or that :func:`pandas.read_csv`
        interprets as a NaN)
    :param str description:
        Optional description for the specific field or property being
        validated. It should not contain the field name or settings.
    :param bool unique:
        Set to True to raise an error in case of duplicate values.
        When FuzzyField instances are used as class attributes, the uniqueness
        check is performed across all instances of the host class and its
        subclasses.
    :ivar str name:
        Name of the field being validated.
        This is set automatically:

        - when FuzzyField instances are used as class attributes, by
          :meth:`FuzzyField.__set_name__`, or by :meth:`FuzzyField.__set__`
          for instance-specific fuzzyfields
        - when FuzzyField instances are used within the :doc:`dictreader`
          framework, by :meth:`DictReader.__init__`
    :ivar bool required:
        as the parameter
    :ivar default:
        as the parameter
    :ivar str description:
        as the parameter
    :ivar bool unique:
        as the parameter
    :ivar set seen_values:
        Record of already encountered values.
        This attribute only exists if unique=True.
    :ivar owner:
        The class to which the FuzzyField is attached to as a descriptor.
        None when used within the :doc:`dictreader` framework.
    """
    def __init__(self, *, required: bool = True, default: Any = None,
                 description: str = None, unique: bool = False):
        self.required = required
        self.default = default
        self.description = description
        self.unique = unique
        if self.unique:
            self.seen_values = set()
        self.name = None
        self.owner = None

    @staticmethod
    def preprocess(value: Any) -> Any:
        """Perform initial cleanup of a raw input value. This method is
        automatically invoked before :meth:`FuzzyField.validate`.

        :param value:
            raw input value
        :returns:
            the argument, stripped of leading and trailing whitespace
            and carriage returns if it is a string.
            If the argument is null, return None.
            Otherwise return the argument unaltered.
        """
        if isinstance(value, str):
            value = value.strip()
            if value in NA_VALUES:
                return None
        # Accept NaN in place of an empty string because
        # pandas converts empty cells to NaNs when parsing CSV files
        elif isnull(value):
            return None
        return value

    def validate(self, value: Any) -> Any:
        """Virtual method - to be overridden.
        Validate and reformat value.
        This method is invoked when processing a new value, after
        :meth:`FuzzyField.preprocess` and before
        :meth:`FuzzyField.postprocess`, but only if the value is not None after
        preprocess.

        :param value:
            Input data, already preprocessed by :meth:`FuzzyField.preprocess`.
            Object type could be anything and should be either tested or
            carefully handled through duck-typing.
        :returns:
            Reformatted value, or None if default is to be used.

            .. note::
               Do not return self.default. This is left to
               :meth:`FuzzyField.__set__` and :class:`DictReader`.
               Instead, for any value that equates to null/blank, always
               return None.
        :raises MalformedFieldError, FieldTypeError:
            if the value is not valid
        """
        raise NotImplementedError("Virtual method, must override")

    def postprocess(self, value: Any) -> Any:
        """Post-process the value after validating it and before storing it.
        This method is invoked after :meth:`FuzzyField.validate` and
        tests the ``required`` and ``unique`` flags.

        :raises MissingFieldError:
            if self.required is True and value is None
        :raises DuplicateError:
            if self.unique is True and value is not None and already found
        """
        if value is None:
            if self.required:
                raise MissingFieldError(self.name)
            # Skip uniqueness check
            return self.default

        if self.unique:
            # Exclude the default from the uniqueness check
            if value is None:
                return value

            try:
                if value in self.seen_values:
                    raise DuplicateError(self.name, value)
                hvalue = value
            except TypeError:
                # Unhashable
                hvalue = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                if hvalue in self.seen_values:
                    raise DuplicateError(self.name, value)

            self.seen_values.add(hvalue)

        return value

    def parse(self, value: Any) -> Any:
        """On-the fly parsing and validation for a local variable.

        This is a wrapper around :meth:`~FuzzyField.preprocess` ->
         :meth:`~FuzzyField.validate` -> :meth:`~FuzzyField.postprocess`.

        :param value:
            raw value to be preprocessed and validated
        :param ff_cls:
            subclass of :class:`FuzzyField` that will perform the validation
        :param kwargs:
            init parameters for the ff_cls
        """
        value = self.preprocess(value)
        if value is not None:
            value = self.validate(value)
        value = self.postprocess(value)
        return value

    def copy(self):
        """Shallow copy of self. The seen_values set is recreated as an
        empty set.
        """
        res = object.__new__(type(self))
        res.__dict__.update(self.__dict__)
        if res.unique:
            res.seen_values = set()
        return res

    @property
    def sphinxdoc(self) -> str:
        """Virtual property - to be overridden.
        Automated documentation that will appear in Sphinx.
        It should not include the name, owner, required, default, unique, or
        description attributes.
        """
        raise NotImplementedError()

    def __repr__(self) -> str:
        """Fancy print the description of the fuzzyfield and all the
        relevant settings. Used when building the docstring of the host class.

        Internally invokes :meth:`FuzzyField.sphinxdoc`.
        """
        res = f"Name\n    {self.name}\n"
        res += f"Type\n    {self.__class__.__name__}\n"
        res += f"required\n    {self.required}\n"
        if not self.required:
            res += f"Default\n    {self.default}\n"
        res += f"Unique\n    {self.unique}\n"
        res += f"Description\n"
        for row in self.sphinxdoc.splitlines():
            res += f"    {row.strip()}\n"
        if self.description:
            res += "\n"
            for row in self.description.splitlines():
                res += f"    {row.strip()}\n"
        return res

    # Extra methods for when the FuzzyField is used as a class property of a
    # generic python class, e.g. not inside a DictReader. See:
    # https://docs.python.org/3/reference/datamodel.html#implementing-descriptors

    def __get__(self, instance, owner) -> Any:
        """Retrieve stored value of the property.

        :returns:
            stored value, or self.default is the stored value is None
            When invoked as a class property, return the FuzzyField object
            itself.

        One may wish to postprocess the return value before it is returned.
        This can be achieved by overriding this method as follows::

            def __get__(self, instance, owner):
                value = super().__get__(instance, owner)
                if value is self:
                    return self

                # postprocess value here

                return value
        """
        assert self.name
        assert owner is self.owner
        # Allow accessing FuzzyField objects when inspecting the class
        # prototype
        if not instance:
            return self

        try:
            value = instance.__dict__[self.name]
        except KeyError:
            if not self.required:
                return self.default
            raise AttributeError(
                f'Uninitialised property: {self.owner.__name__}.{self.name}')

        return value

    def __set__(self, instance, value) -> None:
        """Store value of the property for parent object. Can be used in two
        ways:

        - with a regular value to be validated
        - with a new instance of another FuzzyField. This way one can
          override settings with instance-specific ones.
        """
        assert self.name
        try:
            vi_dict = instance._fuzzyfield_instances
        except AttributeError:
            vi_dict = {}

        if isinstance(value, FuzzyField):
            # Override fuzzyfield with instance-specific one
            vi_dict[self.name] = value
            instance._fuzzyfield_instances = vi_dict
            value.name = self.name
            value.owner = self.owner
        else:
            # Regular set value - pass it to the fuzzyfield
            # Switch to instance-specific fuzzyfield, if it exists
            fuzzyfield = vi_dict.get(self.name, self)
            instance.__dict__[self.name] = fuzzyfield.parse(value)

    def __delete__(self, instance) -> None:
        """Delete the attribute on an instance 'instance' of the owner class.
        """
        assert self.name

        try:
            del instance.__dict__[self.name]
        except KeyError:
            raise AttributeError(f'Uninitialised property: {self.name}')

    def __set_name__(self, owner, name: str) -> None:
        """Called at the time the owner class is created.
        The descriptor has been assigned to name.
        """
        self.owner = owner
        self.name = name
        # self.__doc__ is automatically picked up by help(owner) and by Sphinx.
        # It must be a real attribute; we can't just override it with a
        # @property.
        self.__doc__ = repr(self)
