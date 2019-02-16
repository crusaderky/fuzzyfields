try:
    from .version import version as __version__  # noqa: F401
except ImportError:  # pragma: no cover
    raise ImportError('fuzzyfields not properly installed. If you are running '
                      'from the source directory, please instead '
                      'create a new virtual environment (using conda or '
                      'virtualenv) and then install it in-place by running: '
                      'pip install -e .')


from .core import FuzzyField  # noqa: F401
from .dictreader import DictReader  # noqa: F401
from .errors import (ValidationError, MalformedFieldError,  # noqa: F401
                     FieldTypeError, DuplicateError, DomainError,  # noqa: F401
                     MissingFieldError)  # noqa: F401

from .boolean import Boolean  # noqa: F401
from .datetime import Timestamp  # noqa: F401
from .domain import Domain  # noqa: F401
from .numbers import Float, Decimal, Integer, Percentage  # noqa: F401
from .strings import String, RegEx, ISOCodeAlpha  # noqa: F401
