#!/bin/bash

set -eu
cd -P -- "$(dirname -- "$0")"

SYMSYND_MANYLINUX=${SYMSYND_MANYLINUX:-0}
WHEEL_OPTIONS=

# If we are building on OS X we make sure that our platform version is compiled
# OSX SDK 10.9 and then we ensure that we are building all our stuff with that
# version of the SDK as well.  We accept any python version that is compiled
# against that sdk or older.
#
# Since we build the libsymbolizer separately it's important the same deployment
# target is also used in the libsymbolizer/build.sh so we do it there as well.
#
# For the demangler we set the deployment target to 10.9 in setup.py itself.
if [ `uname` == "Darwin" ]; then
  python -c "if 1:
    import sys
    from distutils.util import get_platform
    ver = tuple(int(x) for x in get_platform().split('-')[1].split('.'))
    if ver > (10, 9):
        print 'abort: python is compiled against an OS X that is too new'
	sys.exit(1)
  "
  export MACOSX_DEPLOYMENT_TARGET=10.9
  WHEEL_OPTIONS="--plat-name=macosx-10.9-intel"
fi

# Since we do not link against libpython we can just use any of the Pythons
# on the system to generate a while (UCS2/UCS4 does not matter).  The dockerfile
# enables one of them already so we go with that.
# In case we would want multiple builds in the future we would need to delete
# .eggs and build between the builds.
if [ x$SYMSYND_MANYLINUX == x1 ]; then
  for py in cp27-cp27mu cp33-cp33m cp34-cp34m cp35-cp35m; do
    pybin="/opt/python/$py/bin"
    $pybin/pip install wheel
    $pybin/python setup.py bdist_wheel $WHEEL_OPTIONS
  done

  echo "Auditing wheels"
  for wheel in dist/*-linux_*.whl; do
    auditwheel repair $wheel -w dist/
    rm $wheel
  done

# Otherwise just build with the normal python and embrace it.
else
  pip install wheel
  python setup.py bdist_wheel $WHEEL_OPTIONS
fi
