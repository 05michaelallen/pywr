#!/usr/bin/env python

try:
    from setuptools import setup
    from setuptools import Extension
    print('Using setuptools for setup!')
except ImportError:
    from distutils.core import setup
    from distutils.extension import Extension
    print('Using distutils for setup!')
from distutils.errors import CCompilerError, DistutilsExecError, \
    DistutilsPlatformError
from Cython.Distutils import build_ext
from Cython.Build import cythonize
import numpy as np
import sys

setup_kwargs = {
    'name': 'pywr',
    'version': '0.1',
    'description': 'Python Water Resource model',
    'author': 'Joshua Arnott',
    'author_email': 'josh@snorfalorpagus.net',
    'url': 'http://snorf.net/pywr/',
    'packages': ['pywr', 'pywr.solvers', 'pywr.domains'],
}

extensions = [
    Extension('pywr._core', ['pywr/_core.pyx'],
              include_dirs=[np.get_include()],),
    Extension('pywr._parameters', ['pywr/_parameters.pyx'],
              include_dirs=[np.get_include()],),
    Extension('pywr._recorders', ['pywr/_recorders.pyx'],
              include_dirs=[np.get_include()],),
]

# HACK: optional features are too difficult to do properly
# http://stackoverflow.com/a/4056848/1300519
optional = set()
if '--with-glpk' in sys.argv:
    optional.add('glpk')
    sys.argv.remove('--with-glpk')
if '--with-lpsolve' in sys.argv:
    optional.add('lpsolve')
    sys.argv.remove('--with-lpsolve')
if not optional:
    # default is to attempt to build everything
    optional.add('glpk')
    optional.add('lpsolve')

compiler_directives = {}
if '--enable-profiling' in sys.argv:
     compiler_directives['profile'] = True
     sys.argv.remove('--enable-profiling')

extensions_optional = []
if 'glpk' in optional:
    extensions_optional.append(
        Extension('pywr.solvers.cython_glpk', ['pywr/solvers/cython_glpk.pyx'],
                  include_dirs=[np.get_include()],
                  libraries=['glpk'],),
    )
if 'lpsolve' in optional:
    extensions_optional.append(
        Extension('pywr.solvers.cython_lpsolve', ['pywr/solvers/cython_lpsolve.pyx'],
                  include_dirs=[np.get_include()],
                  libraries=['lpsolve55'],),
    )

# Optional extension code from Bob Ippolito's simplejson project
# https://github.com/simplejson/simplejson

if sys.platform == 'win32' and sys.version_info > (2, 6):
    # 2.6's distutils.msvc9compiler can raise an IOError when failing to
    # find the compiler
    # It can also raise ValueError http://bugs.python.org/issue7511
    ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError,
                  IOError, ValueError)
else:
    ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)

class BuildFailed(Exception):
    def __init__(self, exc_info):
        self.exc_info = exc_info


class ve_build_ext(build_ext):
    # This class allows C extension building to fail.

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildFailed(e)

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors:
            raise BuildFailed(sys.exc_info())

setup_kwargs['cmdclass'] = {}

# attempt to build the cython solver extensions
success = []
failure = []
for extension in extensions_optional:
    setup_kwargs['ext_modules'] = cythonize([extension], compiler_directives=compiler_directives)
    setup_kwargs['cmdclass']['build_ext'] = ve_build_ext
    try:
        setup(**setup_kwargs)
    except BuildFailed as e:
        failure.append((extension, e))
    else:
        success.append(extension)

if not success:
    for ext, excep in failure:
        print('Build failed for extension: {}'.format(ext.name))
        import traceback
        traceback.print_exception(*excep.exc_info)
    raise BuildFailed('None of the solvers managed to build')

# build the core extension(s)
setup_kwargs['ext_modules'] = cythonize(extensions, compiler_directives=compiler_directives)
del(setup_kwargs['cmdclass']['build_ext'])
setup(**setup_kwargs)

print('\nSuccessfully built pywr with the following extensions:')
for extension in success:
    print('  * {}'.format(extension.name))
