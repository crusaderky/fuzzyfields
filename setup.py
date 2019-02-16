#!/usr/bin/env python
import os
import re
import warnings
from setuptools import find_packages, setup


MAJOR = 2
MINOR = 0
MICRO = 0
ISRELEASED = False
VERSION = '%d.%d.%d' % (MAJOR, MINOR, MICRO)
QUALIFIER = ''


DISTNAME = 'fuzzyfields'
LICENSE = 'Apache'
AUTHOR = 'crusaderky'
AUTHOR_EMAIL = 'crusaderky@gmail.com'
URL = 'https://github.com/crusaderky/fuzzyfields'
CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Intended Audience :: Developers',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Topic :: Scientific/Engineering',
]

INSTALL_REQUIRES = []
EXTRAS_REQUIRE = {
    'Timestamp': [
        'pandas >= 0.23',
        'numpy >= 1.11',
    ]
}
TESTS_REQUIRE = ['pytest >= 3.6']

DESCRIPTION = "fuzzyfields"
LONG_DESCRIPTION = """

"""  # noqa

# Code to extract and write the version copied from pandas.
# Used under the terms of pandas's license.
FULLVERSION = VERSION
write_version = True

if not ISRELEASED:
    import subprocess
    FULLVERSION += '.dev'

    pipe = None
    for cmd in ['git', 'git.cmd']:
        try:
            pipe = subprocess.Popen(
                [cmd, "describe", "--always", "--match", "v[0-9]*"],
                stdout=subprocess.PIPE)
            (so, serr) = pipe.communicate()
            if pipe.returncode == 0:
                break
        except BaseException:
            pass

    if pipe is None or pipe.returncode != 0:
        # no git, or not in git dir
        if os.path.exists('fuzzyfields/version.py'):
            warnings.warn(
                "WARNING: Couldn't get git revision,"
                " using existing fuzzyfields/version.py")
            write_version = False
        else:
            warnings.warn(
                "WARNING: Couldn't get git revision,"
                " using generic version string")
    else:
        # have git, in git dir, but may have used a shallow clone (travis does
        # this)
        rev = so.strip()
        rev = rev.decode('ascii')

        if not rev.startswith('v') and re.match("[a-zA-Z0-9]{7,9}", rev):
            # partial clone, manually construct version string
            # this is the format before we started using git-describe
            # to get an ordering on dev version strings.
            rev = "v%s+dev.%s" % (VERSION, rev)

        # Strip leading v from tags format "vx.y.z" to get th version string
        FULLVERSION = rev.lstrip('v')

        # make sure we respect PEP 440
        FULLVERSION = FULLVERSION.replace("-", "+dev", 1).replace("-", ".")

else:
    FULLVERSION += QUALIFIER


def write_version_py(filename=None):
    cnt = """\
version = '%s'
short_version = '%s'
"""
    if not filename:
        filename = os.path.join(
            os.path.dirname(__file__), 'fuzzyfields', 'version.py')

    a = open(filename, 'w')
    try:
        a.write(cnt % (FULLVERSION, VERSION))
    finally:
        a.close()


if write_version:
    write_version_py()

setup(name=DISTNAME,
      version=FULLVERSION,
      license=LICENSE,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      classifiers=CLASSIFIERS,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      tests_require=TESTS_REQUIRE,
      python_requires='>=3.6',
      url=URL,
      packages=find_packages(),
      package_data={'fuzzyfields': ['tests/data/*']})
