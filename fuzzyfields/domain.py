import pickle
from typing import Any, Iterable
from .core import FuzzyField
from .errors import DomainError, FieldTypeError, MalformedFieldError
from .numbers import Float


_float_parser = Float()


class Domain(FuzzyField):
    """A field which can only accept a specific set of values

    :param choices:
        collection of acceptable values. The default needs not be included.
    :param bool case_sensitive:
        ignore case when validating string input.
        The output will be converted to the case listed in choices.
    :param bool passthrough:
        If True, store the choices object by reference and assume it will
        change after this class has been initialised.
        The change will be reflected in the next parsed value.

        Example::

          v1 = String("ID", unique=True)
          v2 = Domain("CrossRef", domain=v1.seen_values, passthrough=True)

        In the above example, the field 'CrossRef' must be one of the values
        that already appeared for the field 'ID'.

        passthrough comes with a performance cost; set it to False
        (the default) to allow for optimisations. This assumes that neither
        the choices collection nor the objects it contains will change in the
        future.

    :param kwargs:
        extra parameters for :class:`FuzzyField`
    """
    choices: Iterable
    case_sensitive: bool
    passthrough: bool

    def __init__(self, choices: Iterable, *, case_sensitive: bool = True,
                 passthrough: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.choices = choices
        self.case_sensitive = case_sensitive
        self.passthrough = passthrough
        if not passthrough:
            self._parse_choices()

    def _parse_choices(self) -> None:
        """Parse choices and update several cache fields.
        This needs to be invoked after every time choices changes.
        """
        self._has_numeric_choices = False
        self._choices_map = {}

        for v in self.choices:
            k = v
            if isinstance(v, str) and not self.case_sensitive:
                k = v.lower()
            elif isinstance(v, (int, float, complex)):
                self._has_numeric_choices = True
            try:
                self._choices_map[k] = v
            except TypeError:
                k = pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)
                self._choices_map[k] = v

        # Build sorted list of choices, used for string representations
        try:
            sorted_choices = sorted(self.choices)
        except TypeError:
            # choices is a mix of incomparable types, e.g. (1, '2')
            sorted_choices = sorted(self.choices, key=str)
        self._choices_str = ",".join(str(choice) for choice in sorted_choices)
        if len(self._choices_str) > 200:
            self._choices_str = self._choices_str[:200] + '...'

    def validate(self, value: Any) -> Any:
        """Validate and convert the input

        :raises DomainError:
            if the value is not one of the defined choices
        """
        if self.passthrough:
            self._parse_choices()

        k = value
        if isinstance(value, str) and not self.case_sensitive:
            k = k.lower()

        # This first paragraph quickly satisfies most use cases.
        # Note that this returns the representation provided in the choices;
        # e.g. Domain(choices=[1]).parse(1.0) returns 1
        try:
            return self._choices_map[k]
        except KeyError:
            pass
        except TypeError:
            # Unhashable
            k = pickle.dumps(k, protocol=pickle.HIGHEST_PROTOCOL)
            try:
                return self._choices_map[k]
            except KeyError:
                pass

        # Deal with string representation of numbers
        if self._has_numeric_choices and isinstance(k, str):
            try:
                k = _float_parser.validate(k)
            except (FieldTypeError, MalformedFieldError):
                pass
            else:
                try:
                    return self._choices_map[k]
                except KeyError:
                    pass

        raise DomainError(self.name, value, self._choices_str)

    @property
    def sphinxdoc(self) -> str:
        if self.passthrough:
            if not self.choices:
                return "Choice from a domain (dynamically defined at runtime)"
            self._parse_choices()

        return f"Any of: {self._choices_str}"
